# AFL++ — code-level analysis

## 1. Architecture overview

AFL++ ships a monolithic fuzzer binary (`afl-fuzz`) that talks to an instrumented target over a forkserver protocol on three shared resources: two pipes plus a shared-memory edge bitmap. Everything the fuzzer knows about the world is carried in a single `afl_state_t` struct allocated with `calloc` in `main()` at `src/afl-fuzz.c:690` and threaded explicitly through every function (no globals for per-instance state). The struct itself is declared at `include/afl-fuzz.h:562-975` and embeds the lower-level `afl_forkserver_t fsrv` (`include/afl-fuzz.h:567`) plus `sharedmem_t shm` for the coverage map, env-vars cache, MOpt PSO state, queue head, virgin/crash/timeout bitmaps, and ~400 other fields.

`main()` parses arguments with a long `getopt` (`src/afl-fuzz.c:755`), calls `afl_state_init` and `afl_fsrv_init`, then drops into the core loop at `src/afl-fuzz.c:3395`:

```c
while (likely(!afl->stop_soon)) {
    cull_queue(afl);
    ...
    skipped_fuzz = fuzz_one(afl);                  // src/afl-fuzz.c:3664
    ...
    maybe_sync_fuzzers(afl, cur_time, &sync_interval_cnt);
}
```

`fuzz_one` (in `src/afl-fuzz-one.c`, with the main body `fuzz_one_original` at line 328) is the per-seed deterministic + havoc + splice pipeline; `cull_queue` re-selects the favored set; `sync_fuzzers` imports queue entries from sibling nodes. The fuzzer process and the target process are completely separate executables — AFL++ does not link the target in. The bridge is the forkserver embedded by the instrumentation into the target.

## 2. Source tree layout

- `src/` — the `afl-fuzz` binary itself, split into ~25 files by concern: `afl-fuzz.c` (main + loop), `afl-fuzz-one.c` (stages), `afl-fuzz-bitmap.c` (coverage diff), `afl-fuzz-queue.c` (seed scheduling), `afl-fuzz-run.c` (target execution wrappers), `afl-fuzz-redqueen.c` (input-to-state / cmplog), `afl-fuzz-state.c` (`afl_state_init`, `src/afl-fuzz-state.c:76`), `afl-fuzz-mutators.c` and `afl-fuzz-python.c` (custom-mutator plumbing), `afl-forkserver.c` (forkserver client side). Standalone tools live here too: `afl-cc.c` (compiler driver), `afl-showmap.c`, `afl-tmin.c`, `afl-analyze.c`, `afl-cmin.c`, `afl-ld-lto.c`.
- `include/` — public headers shared across binaries. `afl-fuzz.h` defines `afl_state_t`; `forkserver.h` defines `afl_forkserver_t` and Nyx plugin vtable (`include/forkserver.h:80-103`); `cmplog.h` defines the cmplog SHM layout; `config.h` holds tunable constants; `types.h` declares the `FS_*` protocol bitfields (`include/types.h:40-73`).
- `instrumentation/` — every compile-time pass plus the runtime that gets statically linked into the target: `afl-llvm-pass.so.cc` (classic AFL legacy-PM pass), `SanitizerCoveragePCGUARD.so.cc` and `SanitizerCoverageLTO.so.cc` (the newer PCGUARD-based passes used by default), `afl-llvm-lto-instrumentlist.so.cc` (allowlist for LTO), the laf-intel passes (`split-compares-pass.so.cc`, `split-switches-pass.so.cc`, `compare-transform-pass.so.cc`), the cmplog passes (`cmplog-instructions-pass.cc`, `cmplog-routines-pass.cc`, `cmplog-switches-pass.cc`), GCC-plugin twins (`afl-gcc-pass.so.cc`, `afl-gcc-cmplog-pass.so.cc`), and `afl-compiler-rt.o.c` — the single ~3,663-line C file containing the forkserver, SHM setup, persistent-mode helpers, dictionary phone-home, cmplog hooks, and ASAN integration that ends up in every instrumented binary.
- `qemu_mode/` — out-of-tree wrapper around a `qemuafl` git submodule. `build_qemu_support.sh` clones the submodule pinned by `QEMUAFL_VERSION`, runs `./configure --target-list="${CPU_TARGET}-linux-user"` (`qemu_mode/build_qemu_support.sh:206`) and copies the resulting `qemu-${CPU_TARGET}` binary out as `afl-qemu-trace`. Companion shared libs under `libqasan` (QEMU ASAN), `libcompcov` (compcov for QEMU), `unsigaction`, `fastexit`, `hooking_bridge`.
- `frida_mode/` — equivalent for Frida Stalker. The actual instrumentation transformer lives in `frida_mode/src/instrument/instrument.c`; `stalker.c` configures the GumStalker (`frida_mode/src/stalker.c:58-138`).
- `unicorn_mode/`, `nyx_mode/`, `coresight_mode/` — same pattern: a thin AFL++ side plus a build script that fetches a pinned external project (unicornafl, libnyx + QEMU-Nyx).
- `utils/` — auxiliary shared objects and helper programs: `aflpp_driver/aflpp_driver.c` (libFuzzer entry-point shim), `libdislocator/` (heap allocator that hard-faults on small overflows), `libtokencap/` (LD_PRELOAD that captures string comparisons to extend dictionaries), `afl_proxy/` (template for fuzzing targets that aren't local processes), `argv_fuzzing/`, `afl_network_proxy/`, persistent-mode examples.
- `custom_mutators/` — bundled mutator plugins, each a directory: `radamsa/`, `libfuzzer/` (a full libFuzzer source tree), `gramatron/`, `atnwalk/`, `autotokens/`, `honggfuzz/`, `libafl_base/`, `libafl_nautilus/`, `symcc/`, `symqemu/`, `aflpp_tritondse/`, `grammar_mutator/`. All loaded at runtime via `dlopen`.

## 3. LLVM compiler wrappers

`afl-cc.c` is a single 3,951-line C driver. It decides which downstream compiler to invoke and which passes to load based on (1) its `argv[0]`, (2) env vars, and (3) command-line flags, in that order. The mode enums are at `src/afl-cc.c:75-103`:

```c
typedef enum {
  INSTRUMENT_DEFAULT=0, INSTRUMENT_CLASSIC=1, INSTRUMENT_PCGUARD=2,
  INSTRUMENT_CFG=3, INSTRUMENT_LTO=4, INSTRUMENT_LLVMNATIVE=5,
  INSTRUMENT_GCC=6, INSTRUMENT_CLANG=7, ...
} instrument_mode_id;
```

Symlinks `afl-clang-fast`, `afl-clang-lto`, `afl-gcc-fast`, etc. all point at `afl-cc`; `compiler_mode_by_callname` (`src/afl-cc.c:653`) reads `argv[0]` to pick `LTO`, `LLVM`, `GCC_PLUGIN` or plain `CLANG`. The actual pass insertion happens around `src/afl-cc.c:3660-3760`. For modern LLVM the driver uses `-fpass-plugin=<path>` (`src/afl-cc.c:275`), located by walking standard install dirs in `find_object`. Order matters: laf-intel passes (`split-switches-pass.so`, `compare-transform-pass.so`, `split-compares-pass.so`) load first if `AFL_LLVM_LAF_*` is set; then cmplog (`cmplog-switches-pass.so`, `split-switches-pass.so`); then the coverage pass — either `afl-llvm-pass.so` (classic edge XOR), `add_optimized_pcguard` (PCGUARD, the current default), `add_native_pcguard` (vanilla SanitizerCoverage), or LTO via `add_lto_passes` (`src/afl-cc.c:3718`); then `cmplog-instructions-pass.so` and `cmplog-routines-pass.so` if cmplog mode is set (`src/afl-cc.c:3747-3750`); finally `injection-pass.so` for SQLi/LDAP/XSS sinks. The classic pass `afl-llvm-pass.so` inserts at every BB the standard XOR-of-cur-and-prev edge formula, picking `cur_loc = AFL_R(map_size)` at compile time (`instrumentation/afl-llvm-pass.so.cc:551`). PCGUARD and LTO use SanitizerCoverage with AFL++ post-processing to get collision-free assignment.

## 4. Forkserver protocol

The two pipes are at fixed FDs 198 and 199 — `#define FORKSRV_FD 198` in `include/config.h:471`. The target reads commands on `FORKSRV_FD` (control) and writes status on `FORKSRV_FD+1` (status). On the fuzzer side these are the dup'd `fsrv->fsrv_ctl_fd` and `fsrv->fsrv_st_fd` (`include/forkserver.h:120-121`).

`__afl_start_forkserver` (`instrumentation/afl-compiler-rt.o.c:1062`) implements the child side. The version-1 handshake (`include/types.h:53-58`) goes:

1. Child writes 4-byte greeting `0x41464c00 | FS_NEW_VERSION_MAX` (`afl-compiler-rt.o.c:1074, 1137`).
2. Fuzzer replies with the bitwise NOT for echo verification (`afl-compiler-rt.o.c:1148`).
3. Child writes an options bitmap built from `FS_NEW_OPT_MAPSIZE | FS_NEW_OPT_SHDMEM_FUZZ | FS_NEW_OPT_AUTODICT | FS_OPT_IJON` (`afl-compiler-rt.o.c:1156-1166`).
4. Per-option payloads follow: 4-byte map size, then the autodict length+blob (`afl-compiler-rt.o.c:1177-1217`).
5. Final welcome echo of the version, after which the loop at line 1227 begins.

The fuzzer-side parser is at `src/afl-forkserver.c:1188-1590` and walks the same bitfields, including the legacy fallback path for old AFL targets that send `FS_OPT_ENABLED` rather than a version word.

The steady-state per-execution dance is four pipe operations (`afl-compiler-rt.o.c:1227-1366` / `src/afl-forkserver.c:2214-2320`): parent writes `was_killed` flag, child `fork()`s (or in persistent mode just `SIGCONT`s the stopped child), child writes its PID, parent `waitpid`s, child writes the `wait` status. Persistent mode is the same loop with one twist — the child stops itself via `SIGSTOP` after each iteration and the parent uses `WUNTRACED` (`afl-compiler-rt.o.c:1343`, `WIFSTOPPED` check at line 1355) to detect that, so no `fork()` is needed for the next case. The user-facing helper is `__afl_persistent_loop(unsigned max_cnt)` at `afl-compiler-rt.o.c:1373`, which `LLVMFuzzerTestOneInput`-style harnesses wrap around their per-iteration body.

The coverage bitmap is not part of the wire protocol — it lives in a shared-memory segment whose ID is passed via the `__AFL_SHM_ENV` env var. The target writes hits into it during execution; the fuzzer reads it after each iteration. There's no "new edge" signal; the fuzzer always re-classifies the whole map.

## 5. Coverage bitmap (`__afl_area_ptr`)

The map pointer is a global in the target (`instrumentation/afl-compiler-rt.o.c:168`): `u8 *__afl_area_ptr = __afl_area_initial`. `MAP_SIZE_POW2 = 16` and `MAP_SIZE = 65536` (`include/config.h:495-499`) is the historical default, but the size is now negotiated at startup and can be overridden by `AFL_MAP_SIZE`; `MAP_INITIAL_SIZE = 2 << 20` (2 MiB) is what gets `mmap`'d initially to absorb targets compiled with non-colliding (PCGUARD/LTO) coverage at higher cardinality.

Edge hashing for the classic pass is the textbook AFL formula in `__afl_trace` (`afl-compiler-rt.o.c:341-360`):

```c
PREV_LOC_T prev = __afl_prev_loc[0];
__afl_prev_loc[0] = (x >> 1);
u8 *p = &__afl_area_ptr[prev ^ x];
*p += 1 + ((u8)(1 + *p) == 0);     // NeverZero saturating increment
```

`prev` is shifted by 1 so that A→B and B→A hash to different cells. The `1 + ((u8)(1+*p)==0)` is AFL++'s "NeverZero" trick: on overflow the counter wraps to 1 instead of 0.

Post-exec, the fuzzer bucketizes hit counts in `classify_counts` (`include/coverage-64.h:64`) using a precomputed `count_class_lookup16[65536]` table (`src/afl-fuzz-bitmap.c:32`). The 16-bit table is itself derived from an 8-bit table at `src/afl-fuzz-bitmap.c:48-73`:

```c
[0]=0, [1]=1, [2..3]=2, [4..7]=4, [8..15]=8,
[16..31]=16, [32..63]=32, [64..127]=64, [128..255]=128
```

so counters collapse into 9 log-spaced buckets — a hit count of 6 and 7 read as "the same edge", but 7 and 8 read as different. The 16-bit lookup lets `classify_counts` process the map word-at-a-time and skip zero u64s entirely (`coverage-64.h:73`), which on a 2 MiB map is most of the work.

## 6. cmplog mode

The cmplog SHM layout in `include/cmplog.h:84-89` is `struct cmp_map { cmp_header headers[65536]; cmp_operands log[65536][32]; }` — 65,536 hashed comparison sites, up to 32 captured (v0, v1) operand pairs per site, each operand up to 256 bits. The 16-bit `cmp_header` (`cmplog.h:48-55`) packs `hits:6`, `shape:5` (operand width-1), `type:1` (instruction vs routine), `attribute:4` (eq/lt/le/…) into 2 bytes. Routine captures use `cmpfn_operands` (`cmplog.h:71-80`) with two 32-byte buffers to hold the actual memory contents around `memcmp`/`strcmp` call sites.

The compile-time side has two passes. `cmplog-instructions-pass.cc` injects a call to `__cmplog_ins_hookN` (N = 1, 2, 4, 8, 16) before every `icmp`/`fcmp`, passing the two operands and an attribute byte. `cmplog-routines-pass.cc` replaces `memcmp`, `strcmp`, `strncmp`, etc. with `__cmplog_rtn_hook*` shims that snapshot up to 32 bytes from each pointer. The runtime hooks live in `afl-compiler-rt.o.c:2356-2480+` and write into `__afl_cmp_map` (`afl-compiler-rt.o.c:286, 873`), which is mmap'd into a shared segment when `__AFL_CMPLOG_SHM_ID` is set.

Cmplog requires building the same target *twice*: once normally for fast coverage runs, and once with cmplog passes for the heavy operand-capture run. The fuzzer is launched with `-c <cmplog_binary>` and maintains a second `cmplog_fsrv` forkserver (`src/afl-fuzz-cmplog.c:30`). When a seed looks promising, `fuzz_one` triggers the redqueen / input-to-state stage in `src/afl-fuzz-redqueen.c`: `colorization` (line 295) randomizes input bytes to find which positions affect which cmplog entries, then `its_fuzz` (line 554) substitutes captured operand values into those positions — the classic "if `strcmp(x, "MAGIC")`, write `MAGIC` into the input at the right offset."

## 7. qemu_mode

The actual TCG patches do *not* live in this tree — `qemu_mode/` only contains the build harness. `build_qemu_support.sh:32` reads a pinned commit from `QEMUAFL_VERSION`, `git submodule update`s (or clones from GitHub) the separate `AFLplusplus/qemuafl` repo into `qemu_mode/qemuafl/` (`build_qemu_support.sh:73-105`), checks out that commit, then configures and builds the linux-user target (`build_qemu_support.sh:206, 278`):

```sh
--target-list="${CPU_TARGET}-linux-user" ...
cp -f "build/${CPU_TARGET}-linux-user/qemu-${CPU_TARGET}" "../../afl-qemu-trace"
```

The result is a single `afl-qemu-trace` binary in the AFL++ root. At fuzz time `afl-fuzz -Q` prepends this binary to argv. Inside the patched QEMU, every newly translated TCG basic block gets a prologue that XORs the block PC into `prev_loc` and bumps the corresponding cell of the AFL bitmap (the same SHM segment AFL would use natively, attached via env var), and `__afl_start_forkserver` is called once the guest reaches `main` or `AFL_ENTRYPOINT`. AFL++'s tree also ships companion helpers: `libqasan/` (a QEMU-side rebuild of ASAN that operates on guest addresses), `libcompcov/` (compcov for QEMU — instrumented `memcmp`/`strcmp` substitution to give the fuzzer per-byte progress), `unsigaction/` (LD_PRELOAD that swallows guest signal handlers so AFL sees crashes), `fastexit/` (skips libc exit handlers to speed iteration).

## 8. frida_mode

The same "binary-only fuzzing" service for platforms where running a patched QEMU is impractical (macOS, Android, anything ARM where QEMU's linux-user mode is awkward). The implementation is a Frida `gum_stalker` transformer. `stalker_init` (`frida_mode/src/stalker.c:94-138`) creates a `GumStalker` with configurable IC entry count and a custom `GumAflStalkerObserver` (line 21) — the Stalker observer interface is how Frida lets the host hook block transitions.

The transformer callback is `instrument_basic_block` at `frida_mode/src/instrument/instrument.c:157`. It iterates over the instructions of each newly seen block, and on the first instruction inserts a callout to `on_basic_block`. `on_basic_block` (line 106-155) computes the edge ID with the canonical formula on hashed PCs:

```c
guint64 current_pc = instrument_get_offset_hash(current_rip);  // xxh3-based
edge = current_pc ^ *instrument_previous_pc_addr;
instrument_increment_map(edge);                                 // NeverZero++
*instrument_previous_pc_addr = util_rotate(current_pc, 1, map_size_pow2);
```

Default map size for frida is bumped to 64 KiB (`FRIDA_DEFAULT_MAP_SIZE`, `instrument.c:23`). Architecture-specific fast paths (`instrument_x64.c`, `instrument_arm64.c`, `instrument_x86.c`, `instrument_arm32.c`) emit the increment inline rather than via a callout when `instrument_optimize` is on, which is the difference between usable and unusable speed in practice.

## 9. Custom mutators

The plugin ABI is defined as function-pointer fields on `struct custom_mutator` in `include/afl-fuzz.h:996-1210`. Required entry points: `void *afl_custom_init(afl_state_t*, unsigned seed)` returns an opaque per-instance handle, `size_t afl_custom_fuzz(void*, u8 *buf, size_t buf_size, u8 **out_buf, u8 *add_buf, size_t add_buf_size, size_t max_size)` produces a mutated buffer, `void afl_custom_deinit(void*)` releases it. Optional hooks let the plugin participate in any phase: `afl_custom_fuzz_count` (how many times to call fuzz this round), `afl_custom_post_process` (transform before write — header fixup, checksumming), `afl_custom_init_trim`/`afl_custom_trim`/`afl_custom_post_trim` (custom seed minimization), `afl_custom_havoc_mutation` + `afl_custom_havoc_mutation_probability`, `afl_custom_queue_new_entry`, `afl_custom_queue_get`, `afl_custom_describe`, `afl_custom_introspection`, `afl_custom_splice_optout`, `afl_custom_fuzz_send`.

The loader in `src/afl-fuzz-mutators.c:177-340` is a straight `dlopen` + `dlsym` walk: `afl_custom_init` and `afl_custom_deinit` are `FATAL` if missing (`afl-fuzz-mutators.c:206, 265`), `afl_custom_fuzz` falls back to the legacy `afl_custom_mutator` name (`afl-fuzz-mutators.c:217`), the rest are silently skipped. Multiple `;`-separated `AFL_CUSTOM_MUTATOR_LIBRARY` entries chain — they're stored in a list and called in order (`afl-fuzz-mutators.c:92-105`).

Python plugins go through `src/afl-fuzz-python.c`, which embeds CPython and adapts the C ABI into `PyObject_CallObject` invocations against a module's `init`/`fuzz`/etc. functions.

Bundled mutators worth knowing about: `radamsa/` is a thin wrapper around Aki Helin's tool. `libfuzzer/` is a full vendored libFuzzer source tree adapted as an in-process mutator — you get libFuzzer's mutation engine driving AFL++'s scheduling. `gramatron/` is a grammar-aware mutator that uses FSA-encoded grammars (CFGs lowered to deterministic automata) for context-free input languages. `atnwalk/` is a tree-walking grammar mutator, `autotokens/` (`autotokens.cpp`) auto-extracts and shuffles tokens from text-like inputs without a grammar definition. `honggfuzz/`, `libafl_base/`, `libafl_nautilus/`, `symcc/`, `symqemu/`, `aflpp_tritondse/` plug in other fuzzers' mutation engines or symbolic-execution-driven mutators.

## 10. What's genuinely novel at the code level

(1) The strict separation between fuzzer (`src/`) and runtime (`instrumentation/afl-compiler-rt.o.c`) communicating through a wire protocol on fixed FDs makes target instrumentation and harness logic upgradeable independently — old targets and new fuzzers stay compatible through `FS_OPT_OLD_AFLPP_WORKAROUND` (`include/types.h:68`), and the runtime can run *without* the fuzzer at all (it just notices the pipe isn't there and silently runs once at `afl-compiler-rt.o.c:1141`). (2) The "binary-only" modes are not in-tree forks: `qemu_mode/`, `frida_mode/`, `unicorn_mode/`, `nyx_mode/`, `coresight_mode/` are all build-script-driven submodule fetches at pinned commits — meaning evaluating AFL++ means evaluating a *family* of repos, and a build that succeeds today may fail if a submodule's upstream rewrites tags. (3) `afl_state_t` is genuinely one giant struct passed by pointer everywhere rather than a maze of globals; combined with the per-file split of `afl-fuzz-*.c` this makes it unusually tractable to read for a fuzzer of this age and feature surface, but the trade-off is that the struct is ~400 fields long (`include/afl-fuzz.h:562-975`) and adding a feature touches it.
