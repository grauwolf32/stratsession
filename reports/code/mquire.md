# mquire — code-level analysis

Trail of Bits, Apache-2.0, Rust 2024 edition, v1.2.5 at the time of analysis. Single workspace crate (`Cargo.toml` declares `name = "mquire"`, no `[workspace]`), library + CLI binary in one. Hard guarantees encoded in `Cargo.toml:50-52`: `unsafe_code = "deny"` and `unwrap_used = "deny"` apply to the whole tree; the few `#[allow(unsafe_code)]` exceptions are scoped to `Mmap::map` calls (`src/snapshot/raw_snapshot.rs:39`, `src/snapshot/lime_snapshot.rs:209`) and the rusqlite vtab `#[repr(C)]` wrappers (`src/bin/mquire/sqlite/database.rs:263, 397`).

## Architecture overview

The library half (`src/lib.rs:9-14`) exposes five modules: `architecture`, `core`, `memory`, `operating_system`, `snapshot`, `utils`. The binary lives entirely under `src/bin/mquire/`. Three subcommands are defined as a single clap enum in `src/bin/mquire/main.rs:58-88` — `Shell { snapshot }`, `Query { snapshot, query, format }`, `Command { snapshot, command_line }`. All three paths in `main.rs:150-247` do the same bring-up: `open_memory()` → `create_architecture()` → `create_operating_system()` (which performs the entire BTF + kallsyms + init_task discovery up front in `LinuxOperatingSystem::new`, `src/operating_system/linux/operating_system.rs:127-164`) → `Database::new()`. The `Database` wrapper (`src/bin/mquire/database/mod.rs:32-51`) owns a `SqliteDatabase` plus a `CommandRegistry`; on construction it calls `register_all_tables` then `load_autostart_files`.

The SQLite virtual-table glue is the wire between SQL and the kernel walkers: every registered `TablePlugin` is exposed as an eponymous SQLite virtual table (`src/bin/mquire/sqlite/database.rs:116-140`), and the `VTab::open` → `VTabCursor::filter` path (`database.rs:363-437`) calls the plugin's `generate(constraints)` on every query. There is no persistent storage — `Connection::open_in_memory()` at `database.rs:59`.

## Module / package layout

- `src/architecture/intel/` — Intel x86_64 architecture trait impl: `architecture.rs`, `page_table_entry.rs`. Single arch supported; `main.rs:104-112` rejects anything else.
- `src/core/` — abstraction traits: `architecture.rs` (Architecture, Endianness, Bitness), `operating_system.rs` (the `OperatingSystem` trait, only 5 methods, `src/core/operating_system.rs:23-40`), `virtual_memory_reader.rs`, plus `entities/` for cross-OS types.
- `src/memory/` — `PhysicalAddress`, `RawVirtualAddress`, `VirtualAddress`, the `Readable` trait used everywhere as `Arc<dyn Readable>`.
- `src/snapshot/` — three loaders described below.
- `src/operating_system/linux/` — the bulk of the implementation (4.5k LoC across `kallsyms.rs` (1397), `operating_system.rs` (677), `maple_tree.rs` (533), `xarray.rs`, `pid_ns_iterator.rs`, `task_struct_iterator.rs`, `btf.rs`, `kernel_version.rs`, `list.rs`, `virtual_struct.rs`, `utils.rs`).
  - `entities/` are pure POD result types.
  - `operating_system/` holds the entity-specific extraction logic — `task.rs`, `network_connection.rs` (1110), `network_interface.rs` (766), `syslog_file.rs`, `dmesg.rs`, `file.rs`, `memory_mapping.rs`, `kernel_module.rs`, `readable_file_linux_object.rs` (the page-cache reader).
- `src/utils/` — readers, scanners, macros.
- `src/bin/mquire/sqlite/` — minimal rusqlite vtab bridge (`database.rs`, `table_plugin.rs`).
- `src/bin/mquire/database/table_plugins/{common,linux}/` — one file per virtual table (`tasks.rs`, `task_open_files.rs`, `network_connections.rs`, `network_interfaces.rs`, `kernel_modules.rs`, `memory_mappings.rs`, `kallsyms.rs`, `dmesg.rs`, `syslog_file.rs`, `boot_time.rs`).
- `src/bin/mquire/commands/{common,linux}/` — `carve.rs`, `system_version.rs`, `dump.rs`, `task_tree.rs`.
- `sql/views/linux/common/` — three autostart SQL views.
- `integration-tests/sql-queries/` — `cfg/`, `snapshots/`, `sql/`, `verifier/` subdirs.

## BTF parsing via btfparse crate

`btfparse` is a separate Trail of Bits crate (v1.3.9 dep in `Cargo.toml:21`, `caching` feature on). mquire does not parse BTF itself; it scans physical memory for the kernel's `.BTF` section and hands each candidate to `btfparse::TypeInformation::new`.

The scanner lives in `src/operating_system/linux/btf.rs`. `BtfBatchScanner::new` (lines 173-200) flattens all `Readable::regions()` into 4 MB chunks and scans them in 64-chunk batches with rayon (`btf.rs:55, 219-222`). Each batch's matches are returned sorted by physical address. For every BTF magic hit (`0x9FEB01` LE or `0xEB9F01` BE — lines 27-36), `BtfHeader::new` (lines 75-95) validates a 24-byte header, then `scan_range_for_btf` (lines 236-296) imposes two cheap structural filters before calling btfparse: payload size in 1 MB..=64 MB (lines 48, 272-275) and `flags == 0 && hdr_len == 24` (line 268). Only after `TypeInformation::new` succeeds does it check `type_information.id_of(".data..percpu").is_some() && type_information.id_of("task_struct").is_some()` (lines 287-289) — the percpu DATASEC plus `task_struct` together are mquire's signature for the vmlinux BTF (distinguishing it from BTF blobs for kernel modules).

The integration point is `BtfparseReadableAdapter` (lines 99-143): mquire's `Readable` is bridged into `btfparse::Readable` with a `base_offset` that anchors BTF-relative offsets in the snapshot. `From<MemoryError> for BTFParseError` (lines 117-122) bridges errors.

What `btfparse` gives that hand-written BTF parsing would not: the full type graph (`TypeInformation::id_of`, `from_id`, `size_of`, `offset_of`, `pointee_tid`) consumed throughout the linux module. The whole `VirtualStruct` API (`src/operating_system/linux/virtual_struct.rs:92-146`) — `from_name(...)`, `traverse("foo.bar[3].baz")` (calling `type_information.offset_of` at line 95), `dereference()` (calling `pointee_tid` at line 127) — is a thin wrapper that turns BTF type IDs into typed reads. Without that, every offset/type relation would have to be hardcoded per kernel version.

## Kallsyms scanner

`src/operating_system/linux/kallsyms.rs` is the largest single file (1397 lines). It requires kernel >= 6.4: every scan helper bails with `ErrorKind::NotSupported` if the version is older (e.g. `kallsyms.rs:499-504, 786-791, 874-879, 1007-1012`). The reason is `commit 404bad70fcf7 "scripts/kallsyms: change the output order"` (cited in `kallsyms.rs:17-22, 1014-1048`); prior to 6.4, the `kallsyms_num_syms` → `kallsyms_names` → `kallsyms_markers` → `kallsyms_token_table` → `kallsyms_token_index` → `kallsyms_offsets` → `kallsyms_relative_base` → `kallsyms_seqs_of_names` order didn't hold and the linux_banner landmark trick fails.

The orchestrating constructor `Kallsyms::new` (`kallsyms.rs:236-378`) chains seven scan passes; each one narrows a `ScanSessionList` (line 223) of candidate kallsyms layouts. If a pass empties the list, init fails. Each pass operates over kernel-virtual ranges in parallel via rayon (`kallsyms.rs:632-772`).

The foundational heuristic is **`scan_for_kallsyms_token_table`** (`kallsyms.rs:492-775`): it scans for the printable-ASCII tokens that always live in the table by searching for the 20-byte digit sequence `"0\01\02\0...9\0"` (lines 515-518), then within a 1 KB window after the hit looks for exactly one uppercase 26-letter run and one lowercase 26-letter run (lines 644-700; "exactly one" is the disambiguator). Then backward-scan (`find_token_table_start`, lines 542-583) walks back until two consecutive nulls or a non-ASCII byte; forward-scan (`find_token_table_end`, lines 588-630) requires exactly 256 null-terminated tokens. The other passes pivot off this anchor:

- `kallsyms_token_index` is bootstrapped by *constructing the expected u16 offset array* from the recovered token-table bytes (`kallsyms.rs:814-841`) and searching for that exact byte pattern within a 10 MB window — an index-from-data check that avoids needing kernel-side heuristics.
- `kallsyms_num_syms` is located by searching backwards from the markers table for the string `"Linux version X.Y.Z"` (`kallsyms.rs:1053-1095`) — the linker layout puts `linux_banner` immediately before `kallsyms_num_syms` in `.rodata` (kernel 6.4+), 8-byte aligned (line 1106).
- `kallsyms_offsets` vs `kallsyms_addresses` is disambiguated by reading the first entry as a u64 and comparing to `KERNEL_VIRTUAL_ADDRESS_BASE = 0xFFFF800000000000` (`kallsyms.rs:115, 1190-1195`): if it looks like a kernel pointer, this is the 8-byte `kallsyms_addresses` layout (CONFIG_KALLSYMS_BASE_RELATIVE=n); otherwise it's 4-byte `kallsyms_offsets`.

Decompression in `decompress_kallsyms` (`kallsyms.rs:395-456`) implements three address-reconstruction strategies based on kernel version (`>= 6.15` removed CONFIG_KALLSYMS_ABSOLUTE_PERCPU per commit `01157ddc58dc`, lines 419-435).

## Snapshot format handling

Format is detected purely by file extension in `open_memory()` (`src/snapshot/mod.rs:38-67`), returning `Arc<dyn Readable>`. Three implementations:

- **Raw** — `src/snapshot/raw_snapshot.rs`. mmaps the file (`raw_snapshot.rs:36-43`, the `unsafe` is scoped here), assumes physical address 0..file_size is the whole RAM range. Reads beyond file size error (lines 52-57).
- **LiME** — `src/snapshot/lime_snapshot.rs`. Parses 32-byte headers (magic `0x4C694D45`, lines 35, 63-124) walking the file linearly. Sparse regions are detected when two `LIME_HEADER_MAGIC` headers appear back-to-back (`lime_snapshot.rs:160-178`) — the gap is recorded as `data_present: false` and zero-filled on read (lines 264-268). AVML compressed dumps are explicitly rejected (`lime_snapshot.rs:72-77`). `Readable::read` binary-searches the range list (`lime_snapshot.rs:224-241`).
- **ELF core** — `src/snapshot/elf_core_snapshot.rs`. Reads ELF header (magic check at line 42, class/data bytes at 45-54), walks PT_LOAD segments, each mapping a physical-address range to a file offset. PT_NOTE / device state ignored.

All three implement `Readable::regions() -> Vec<Range<PhysicalAddress>>`; this is what the BTF scanner consumes to know what to scan.

## SQL virtual table implementation

The bridge is `src/bin/mquire/sqlite/database.rs` + `src/bin/mquire/sqlite/table_plugin.rs`. The `TablePlugin` trait (`table_plugin.rs:104-123`) is intentionally tiny: `schema()`, `name()`, optional `generator_inputs()` for constraint-pushdown columns, and `generate(constraints) -> RowList`. There is no row-streaming API — generation is materialize-then-iterate.

Wiring uses rusqlite's eponymous-only module (`database.rs:116-140`): a `CREATE TABLE name (...)` DDL string is synthesized from the plugin's schema, columns marked `ColumnVisibility::Hidden` are emitted with the SQLite `HIDDEN` keyword (`database.rs:290-296`). `PluginVTab::best_index` (`database.rs:316-361`) inspects equality constraints, matches them against `generator_inputs`, and reports `set_idx_str(&col_names.join(","))` plus `set_estimated_cost(1.0)` for satisfied or `f64::MAX` for unsatisfied — this nudges the planner toward query plans that push constraints in via JOINs. `PluginVTabCursor::filter` (`database.rs:399-437`) decodes `idx_str`, calls `plugin.generate(&constraints)`, stores the full `RowList`, and serves rows from memory. Every query against a virtual table re-invokes `generate` and walks kernel memory fresh — there is no caching.

Three concrete walkers:

- **`tasks`** (`src/bin/mquire/database/table_plugins/linux/tasks.rs`): schema at lines 230-294. `generator_inputs = ["virtual_address", "root_task", "source"]` (lines 301-307). `generate` (lines 309-372) dispatches on the constraint triple. The default (no constraints) merges two independent walks: `task_list` (the `TaskStructIterator` graph traversal) and `pid_ns` (the IDR XArray) — see "Multi-source task discovery" below. A `source` column on every row marks which walk it came from (lines 164-166).
- **`task_open_files`** (`task_open_files.rs`): `generator_inputs = ["task"]` (line 169). If `task` is constrained, calls `iter_task_open_files(task_vaddr)` directly. Without it, iterates all tasks via `system.iter_tasks()` and flat-maps each one's fd table (lines 114-137). Each row carries the file's `virtual_address` and the owning `task` virtual_address — the join key.
- **`network_connections`** (`network_connections.rs`): schema at lines 65-101. `generator_inputs = ["protocol"]` (line 108). `generate` (lines 111-195) calls `LinuxOperatingSystem::iter_network_connections(&protocol_filter)`, which in turn (in `src/operating_system/linux/operating_system/network_connection.rs:557-602`) looks up `tcp_hashinfo` / `udp_table` via kallsyms, parses `inet_hashinfo.lhash2_mask` / `ehash_mask` from BTF (lines 651-714), and constructs a `NetworkConnectionIterator` that walks both the listening hash buckets and the established hash buckets. The `inode` column on each row is the join key into `task_open_files.inode`.

## Custom commands

Commands are dot-prefixed (`.task_tree`, `.dump`, `.carve`, `.system_version`). Registered statically via a macro in `src/bin/mquire/commands/command_registry.rs:160-170`. The `Command` trait (`command_registry.rs:34-43`) is `name() / description() / execute(&str, &CommandContext)`; `CommandContext` (lines 22-31) hands the OS, architecture, and snapshot Arcs.

- **`.system_version`** (`commands/common/system_version.rs:32-51`) — three-line wrapper around `OperatingSystem::get_os_version()`.
- **`.carve`** (`commands/common/carve.rs:332-385`) — takes `(root_page_table, virtual_address, size, output_path)`. Builds a `CarvingPlan` (`carve.rs:93-...`) by enumerating page-table-mapped regions and classifying the carve range into Mapped vs Unmapped subranges; unmapped subranges are zero-filled at write time (`carve.rs:285-313`). Uses 4 MB read buffers (`carve.rs:31`).
- **`.task_tree`** (`commands/linux/task_tree.rs`) — iterates tasks via `iter_tasks()`, builds child/parent maps keyed by tid, optionally toggles `--use_real_parent` / `--show_threads`, then ASCII-prints the tree (`task_tree.rs:60-105`).
- **`.dump`** (`commands/linux/dump.rs`) is the most interesting. Drives across every task's open files, hands each `struct file *` virtual address to `OperatingSystem::get_file_reader(file)` (`dump.rs:138`), then walks the returned `Arc<dyn Readable>` page-by-page out to disk under `tgid_<n>/<sanitized-path>` (lines 95-126, 175-313). Gaps between regions are zero-padded (lines 200-221).

The page-cache reconstruction itself happens in **`src/operating_system/linux/operating_system/readable_file_linux_object.rs`**. `from_file_vaddr` (lines 57-203) starts at the kernel `struct file` (BTF-typed), traverses `f_inode->i_mapping->i_pages` to reach the address space XArray (lines 88-103), and runs `XArray::new` against it. For every entry in the XArray (lines 131-194), it inspects the kernel's `struct folio`: reads `folio.flags` and tests `PG_HEAD_BIT (1<<6)` to decide whether it is a multi-page compound folio (lines 159-172). If multi-page, reads `_folio_nr_pages` or `_nr_pages` (selected at lines 110-129 based on BTF availability — the field was renamed across kernels) and registers all `nr_pages` of consecutive page indices to the same folio (lines 183-186). Folio size is capped at `MAX_FOLIO_PAGES = 512` (`readable_file_linux_object.rs:32, 174-181`). For pre-folio kernels (no `folio` type in BTF), falls back to `struct page.index` (lines 187-193).

The page-to-physical translation in `page_to_phys` (lines 206-212) is the vmemmap inverse: `pfn = (page_vaddr - vmemmap_base) / sizeof(struct page)`, then `phys = pfn * 4096`. `vmemmap_base` is read from kallsyms at startup (lines 64-80). The `Readable::read` impl (lines 215-258) does page-by-page lookup against the cached `BTreeMap<page_index, page_vaddr>`. `regions()` (lines 264-298) coalesces resident pages into runs — this is what `.dump` uses to detect file holes vs evicted pages.

The XArray walker is `src/operating_system/linux/xarray.rs`. `XArray::new` (lines 35-78) implements the kernel's XArray tagging conventions: bottom 2 bits == 0b10 is an internal node pointer minus 2 (lines 197-210), bottom bit == 1 is a value entry (line 213), sibling entries chain via slot offset (lines 222-231). Tree fan-out is read dynamically from BTF (`get_xa_chunk_size`, lines 86-144) by inspecting `xa_node.slots[]`'s array element count, so the parser does not hardcode `XA_CHUNK_SHIFT`.

## Multi-source task discovery for rootkit detection

Two structurally independent walks, both exposed as the `tasks` virtual table:

- **`task_list`** — `src/operating_system/linux/task_struct_iterator.rs`. A BFS over `task_struct` pointers, seeded from `init_task`. The field set walked at lines 138-151 is intentionally aggressive: `last_wakee`, `real_parent`, `parent`, `group_leader`, `pi_top_task`, `oom_reaper_list`, plus the `sibling`, `children`, `thread_node` list-head pairs (with the appropriate `container_of` subtractions). Each candidate has a TTL (`TASK_DISCOVERY_QUEUE_ITEM_TTL = 2`, line 30) that decreases on invalid fields (pid > 4M, missing pointers — lines 236-247) and goes to 0 on read errors. Visited addresses are tracked in a `BTreeSet<RawVirtualAddress>` (line 47, 117) so cycles terminate. The hidden-process detection view comments at `sql/views/linux/common/200_hidden_process_detection.sql:5-7` acknowledge this walk "may occasionally yield invalid entries" — the TTL exists because of this trade-off.
- **`pid_ns`** — `src/operating_system/linux/pid_ns_iterator.rs`. Walks the kernel's IDR (which is itself an XArray since 4.x): `pid_namespace.idr.idr_rt` is fed to `XArray::new` (`pid_ns_iterator.rs:95-110`), yielding `struct pid *` pointers. Each `struct pid` is converted to its `task_struct *` via `tasks[PIDTYPE_PID].first - offsetof(task_struct, pid_links)` (lines 174-205) — proper `container_of`. Default entry point is `init_pid_ns` resolved through kallsyms (`src/operating_system/linux/operating_system/task.rs:240-254`).

Per-source dedup is intra-iterator: `task_list` uses `visited_raw_vaddrs` (`task_struct_iterator.rs:47, 117`), `pid_ns` uses `visited_tasks` (`pid_ns_iterator.rs:65, 218`). Cross-source dedup is **not** done inside the engine — `TasksTablePlugin::generate` simply concatenates rows from both walks (`tasks.rs:334-340`) and tags them with `source = "task_list"` or `source = "pid_ns"`. Deduplication is delegated to SQL: `processes` view uses `SELECT DISTINCT` (`sql/views/linux/common/000_processes.sql:10`), and `hidden_processes` (`200_hidden_process_detection.sql`) does a `FULL OUTER JOIN` on `tl.virtual_address = pn.virtual_address` and flags rows where either side is NULL.

## `virtual_address` as canonical join key

`VirtualAddress` is a 128-bit value: `(root_page_table: PhysicalAddress, raw_virtual_address: RawVirtualAddress)` — `src/memory/virtual_address.rs:21-28`. Two virtual addresses are only comparable if their root page tables match (`virtual_address.rs:70-80, 125-138`); arithmetic operators and `PartialOrd` enforce this. The serialized form (`virtual_address.rs:83-92`) is `vaddr(0x<page_table>, 0x<raw>)`, which round-trips through `FromStr` (lines 100-123). That round-trip is what makes it usable as a string column in SQLite without information loss — every table that exposes object identity uses this column as `ColumnType::String` (`tasks.rs:232-235`, `task_open_files.rs:151-154`, `network_connections.rs:67-70`).

It is also the constraint-pushdown key. `TasksTablePlugin::generator_inputs` returns `["virtual_address", "root_task", "source"]` (`tasks.rs:301-307`); `TaskOpenFilesTablePlugin::generator_inputs` returns `["task"]` (`task_open_files.rs:169`). So a join like

```sql
SELECT * FROM task_open_files tof JOIN tasks t ON tof.task = t.virtual_address
```

causes SQLite (guided by `best_index` cost heuristics in `database.rs:316-361`) to push `tof.task` values one-at-a-time into `TaskOpenFilesTablePlugin::generate`, which then walks only that task's fd table (`task_open_files.rs:88-111`) instead of all tasks. This is what makes the autostart `process_network_connections` view tractable.

## Materialization + integration tests

Three autostart views in `sql/views/linux/common/`, loaded alphabetically by `Database::load_sql_files_from` (`src/bin/mquire/sqlite/database.rs:172-241`) from `$HOME/.config/trailofbits/mquire/autostart/{common|linux}/{common|intel}/`:

- `000_processes.sql` — wraps `tasks` with `WHERE type='thread_group_leader' AND pid>0` in a `MATERIALIZED` CTE then `SELECT DISTINCT` (collapses task_list+pid_ns into one row per process).
- `100_process_network_connections.sql` — three MATERIALIZED CTEs (`network_connections`, `task_open_files`, deduplicated `tasks`) then `JOIN ... ON nc.inode = tof.inode JOIN ... ON tof.task = t.virtual_address`. The `MATERIALIZED` hint matters because each CTE re-invokes the underlying walker — caching them as temp tables prevents repeat full-kernel scans.
- `200_hidden_process_detection.sql` — `FULL OUTER JOIN` of `source='task_list'` against `source='pid_ns'`, surfacing rows where either side is NULL.

Integration tests live under `integration-tests/sql-queries/` with `cfg/`, `snapshots/`, `sql/`, `verifier/` subdirs — a YAML-driven matrix of (snapshot, query, expected) tuples; the structure suggests a test runner that loads a known dump, runs a query, and diffs against a verifier file.

## What is genuinely novel at the code level

The vtab-as-walker pattern itself is not new (osquery), but the implementation choices are. First, the page-cache reconstruction (`readable_file_linux_object.rs`) walks address-space XArrays + folios using BTF for offsets and exposes the reconstructed file as a generic `Arc<dyn Readable>`, so `.dump`, `.carve`, and any future tool consume the same trait — folio-aware file extraction from a memory image with no kernel-version table is uncommon. Second, the kallsyms scanner (`kallsyms.rs`) bootstraps `kallsyms_token_index` by *constructing* the expected u16 array from the recovered token bytes and pattern-matching it back into memory (lines 814-841), avoiding a heuristic and committing to "exactly 256 tokens" as a hard invariant. Third, treating `VirtualAddress = (root_page_table, raw)` as a round-trippable string column makes SQL joins across walks meaningful across address spaces, which the cross-source dedup design (rootkit detection in SQL, not in code) directly depends on.
