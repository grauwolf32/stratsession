# CERT UEFI Parser — code-level analysis

Repo: `sources/dfir/cert-uefi-parser/` (CMU/SEI). Python 3.10+, single distributable package `uefi_parser/`, no `src/` layout.

## Architecture overview

Python package built on top of the `construct` declarative binary-parsing framework (`construct>=2.10.70`, `pyproject.toml:14`). No `__main__.py`; the console script is wired in `pyproject.toml:43` (`cert-uefi-parser = "uefi_parser.cmds:cert_uefi_parser"`) and the entry function lives at `uefi_parser/cmds.py:96`. `cert_uefi_parser()` sets up an `argparse` mutually-exclusive group with `--gui` / `--text` / `--json` / `--sbom` (`cmds.py:102-114`), then `process_file()` (`cmds.py:46`) either runs `AutoObject.parse()` or, with `--brute`, a sliding-window `BruteForceFinder` (`uefi_parser/auto.py:59` and `:136`). All parsed objects descend from one base class `FirmwareStructure` (`uefi_parser/base.py:719`); each subclass declares `definition = Struct(...)` plus optional `reporting` / `sbom_fields`; framework calls `analyze()` / `validate()` after Construct fills the container (`base.py:812-834`). No visitor, no AST — the Construct expression *is* the schema.

## Module / package layout

Flat package `uefi_parser/` (~44 modules; ~184k LOC dominated by `guiddb.py` at 158,123 lines of generated GUID metadata).

Key files:
- `base.py` (1697 LOC; `FirmwareStructure`, custom commit-aware `Struct`, `Class()` wrapper, `SafeFixedLength`, `CommitMystery`, adapters, renderers)
- `auto.py` (top-level `Select(...)`)
- `cmds.py` (CLI)
- `uefi.py` (1580 LOC; FFS / FV / capsules / NVRAM / guided sections)
- `me.py` (2742 LOC; Intel ME — MFS, FTPR, CPD, LLUT)
- `vendor.py` (1824 LOC; FMP, Dell/Huawei/Lenovo updaters, LVFS, CAB, image containers)
- `exes.py` (PE/TE/ELF + `.sbom` PE-section extraction at `exes.py:288-318`)
- `acpi.py`, `amd.py`, `ami.py`, `apple.py`, `coreboot.py`, `flash.py`, `bootguard.py`, `fit.py`, `fsp.py`, `tpm.py`, `smbios.py`, `nvvars.py`, `pfs.py`, `plf.py`, `gecko.py`, `devicetree.py` — one module per format family
- `sbom.py` (uSWID / CoSWID via `uswid`)
- `guiddb.py`
- `gui.py`/`gui_helper.py`/`qhexview.py`/`icon.py` (optional PySide6)
- `mypy.py` (custom plugin, `mypy.py:154`, registered `mypy.ini:10`)
- `test_construct.py` (demo, not tests)

Companion package `cert-uefi-support` is declared as runtime dep (`pyproject.toml:19`) but is **not** in this repo — imported as `uefi_support` (`me.py:70`, `compression.py:34`, `vendor.py:44`, `coreboot.py:37`, `uefi.py:43`) and ships C-accelerated decompressors `HuffmanDecompress`, `Huffman11Decompress`, `LzmaDecompress`, `CabFile`. The Intel ME Huffman codeword tables are why `cert-uefi-support` is distributed separately on PyPI.

## Construct grammar pattern

The key architectural decision: every firmware structure is a Python class whose body is a Construct expression; parsing is `cls.parse(data, offset)`. The custom `Class()` construct (`base.py:650-701`) wraps any `FirmwareStructure` so grammars compose recursively (`Class(OtherStruct)` as a field). The custom `Struct` (`base.py:390`) replaces `construct.Struct` to honor `Commit` markers (`base.py:434-503`): once a "magic" matches, subsequent parsing failures stop unwinding and instead emit a partial object with the unparseable tail captured as `MysteryBytes`.

Example 1 — FFS section grammar (`uefi_parser/uefi.py:650-712`) dispatches on EFI section type with `Switch`:

```python
"data" / FixedLength(this._realsize, Switch(
    lambda ctx: ctx.type, {
        EFISection.Compressed:   Class(CompressedSection),
        EFISection.GuidDefined:  Class(GuidDefinedSection),
        EFISection.PE32:         Class(PEExecutable),
        EFISection.Terse:        Class(TEExecutable),
        EFISection.DxeDepex:     Class(DXEDependency),
        EFISection.Name:         PaddedString(this._realsize, 'utf-16-le'),
        EFISection.Volume:       LazyBind(lazy_safe_firmware_volume),
        EFISection.Raw:          Select(Class(PNGImage), Class(JPGImage), ...,
                                        LazyBind(freeform_guid_class),
                                        Class(MysteryRawBytes)),
    }, default=Class(MysteryBytes)))
```

Example 2 — Intel flash descriptor (`uefi_parser/flash.py:151-190`) uses `Pointer` for absolute-offset jumps to BIOS / ME / GbE / PDR regions, each bounded with `FixedLength` and handed to its own `Class(...)`; the BIOS region opportunistically attempts `Select(LazyBind(lazy_coreboot), Class(BIOSFlashRegion))`.

Why this is more extensible than EDK2 / `uefi-firmware-parser` / `chipsec`: adding a vendor format is one class with a `definition` Struct and a one-line registration in `auto.py:63`'s `Select`. The same definition drives parse, build (`Class._build` at `base.py:694`), JSON serialization (`base.py:1070`), SBOM extraction (`base.py:1128`), text report (`base.py:1300`), and Qt model — no parallel hand-coded paths. The `CommitMystery` discipline isolates per-class failures so a malformed sub-tree degrades to `MysteryBytes` without aborting the whole parse.

## Coverage of proprietary formats

- **Intel ME.** `me.py:30-56` explicitly cites Igor Skochinsky's `me-tools`, Dmitry Sklyarov (BlackHat EU 2017 MFS), Ermolov & Goryachy, Positive Technologies' `unME11` / `parseMFS`, Plato Mavropoulos' `MEAnalyzer`, Reed / Martin's `uefi-firmware-parser`. Implements MEModuleHeader1/2, LLUT, MFS chunks/pages/files/dir, CPD manifests + metadata 4/5/6/7/8/11, manifest types 15/18/18a/22 — all as Construct classes. Huffman decompression in `analyze_huffman()` (`me.py:252-315`) using LLUT lookup tables; the actual codeword tables live in `cert-uefi-support`.
- **Intel flash descriptor.** `flash.py:151` walks descriptor/master/region maps.
- **Vendor capsule / updater formats.** `vendor.py` — FMP capsules (`vendor.py:371`, GUID `6dcbd5ed-...`), Dell updater EFI app (`.biosdat` PE-section re-parse, `vendor.py:435-499`), Dell `PupHeader`/`IPackFile`/`IPackHeader`, Huawei updater EXE, LVFS, MS CAB, JCAT, PGP. EFI1/EFI2/UEFI/AMI capsules at `uefi.py:1396-1559`.
- **AMI PFAT** (`ami.py`), **AMD PSP** (`amd.py`), **Dell PFS** (`pfs.py`), **Lenovo date/time/version** (`uefi.py:927`), **Insyde GAID/ML0W** (`uefi.py:972-1003`), **Parallels NVRAM** (`uefi.py:1560`), **VMware NVRAM** (`nvvars.py`), **Apple Freeforms** (`apple.py` + GUID-keyed dispatcher `freeform_guid_class()` at `uefi.py:571-643` mapping ~40 Apple GUIDs).
- **Boot Guard / FIT / FSP** (`bootguard.py`, `fit.py`, `fsp.py`).

Vendor quirks live in three places: (1) GUID `Switch` tables inside generic structures (`uefi.py:261` `SubtypeGuidSection`, `uefi.py:495` `GuidDefinedSection`, `uefi.py:805` `FreeformFile.interpretation`); (2) `freeform_guid_class()` runtime selector at `uefi.py:572-643`; (3) top-level GUID magics asserted via `Const(<GUID>.bytes_le)` followed by `CommitMystery` (e.g. FMP capsule, EFI1/2 / UEFI capsules, Lenovo date/time at `uefi.py:932`).

## The four output modes

Selected in `cmds.py:77-85`:

- **`--text`** → `result.report()` (`base.py:1300-1418`). Reads per-class `reporting = [...]` declarations (each term is `[field]`, `[field, formatter]`, `[field, fmt, post_lambda]`, or `[]` for line break) and emits ANSI colors via `utils.py:71-102`. `--no-color` flips a module-level global in `cmds.py:156-157` consumed by `utils.emit_color()` at `utils.py:74`.
- **`--json`** → `json.dumps(result.to_dict(True), indent=2)`; `to_dict()` at `base.py:1070-1126` emits every non-underscore field + `_class`/`_offset`/`_length`.
- **`--sbom`** → `json.dumps(result.sbom(), indent=2)`; `sbom()` at `base.py:1128-1170`. This is the filtered SBOM-shape — walks only fields listed in the per-class `sbom_fields` attribute; classes without `sbom_fields` contribute nothing. The dict carries `_class` but deliberately omits `_offset`/`_length` (commented out, `base.py:1168-1169`). Notable shapes:
  - `AutoObject → ["auto"]` (`auto.py:133`)
  - `FirmwareVolume → ["filesystem"]` (`uefi.py:1313`)
  - `FirmwareFileSystem → ["files"]` (`uefi.py:1225`)
  - `FirmwareFileSystemFile → ["guid", "hash", "data"]` (`uefi.py:914`)
  - `FreeformFile → ["guid", "interpretation", "sections"]` (`uefi.py:822`)
  - `FirmwareFileSystemSection → ["data"]` (`uefi.py:721`) with name/version sections collapsed to `{"name": ...}` / `{"version": ...}` (`uefi.py:729-739`)
  - `PEExecutable → ["fshash"]` (`exes.py:275`)
  - `FMPCapsule → ["payloads", "data_files"]` (`vendor.py:423`)
  - `FlashDescriptor → ["bios", "me"]` (`flash.py:190`)
  
  Root key is `auto`, then `filesystem.files[].data` chains down to GUIDs/hashes/names/versions — this is the input shape a CycloneDX HBOM mapping would consume.

- **`--gui`** → lazy `from .gui import run_gui` (`cmds.py:81-83`). Pre-flighted by `gui_helper.ensure_gui_environment()` (`gui_helper.py:94`) which checks PySide6 presence and on Linux verifies `DISPLAY`/`WAYLAND_DISPLAY` plus XCB shared libs (`gui_helper.py:54-89`). `gui.py:214` and `gui.py:328` are `QAbstractItemModel`s; an embedded `QHexView` (`qhexview.py`, 1312 LOC) renders raw bytes; `ansi_to_html()` (`utils.py:65`) converts the text-mode color escapes into HTML for the detail panel (`gui.py:376`). PySide6 is an optional extra: `pyproject.toml:35-37`.

## Type stubs (`stubs/`)

Three trees: `stubs/construct/__init__.pyi` (627 lines hand-written partial stub for `construct`, which ships untyped); `stubs/asn1crypto/cms.pyi` (11 lines) + `stubs/asn1crypto/x509.pyi` (10 lines, minimal forward-decls); `stubs/pefile.pyi` (~41 KB generated). `mypy.ini` enables strict + every `disallow_*`/`warn_*` toggle (`mypy.ini:20-31`) and loads `uefi_parser.mypy` (`mypy.ini:10`). The plugin (`mypy.py:154-207`) inspects every `FirmwareStructure` subclass, enumerates the `definition` Struct's `by_name` map (`mypy.py:106-107`) and `@property` accessors (`mypy.py:111-113`), and overrides `get_attribute_hook` so mypy stops complaining about fields Construct injects at runtime. Actual *typing* of those fields is mostly `Any` — there's a long commented-out `construct_to_mypy_type()` block (`mypy.py:117-152`) showing the intended mapping (FormatField→int, Bytes→bytes, Array→list, Class→FirmwareStructure, UUIDAdapter→UUID). For an agent enforcing mypy strictness against this repo, the plugin is a hard dependency.

## Tests

No real test suite. `uefi_parser/test_construct.py` is a *demo* — its own docstring says "This should probably use the unittest module" (`test_construct.py:27`). Defines `Fake`/`FakeCStruct`/`FakeSubStruct` and one `fake_test()` (`test_construct.py:168`) that builds a synthetic buffer with `struct.pack`, parses, prints, mutates, calls `generate_from_memory()`, compares — no pytest assertions, no automated collection. No `tests/`, `conftest.py`, `pytest.ini`, `tox.ini`. **No sample firmware files** in the repo (verified by `find ... -name "*.fd" -o -name "*.rom" -o -name "*.bin"` returning empty). Downstream consumers must supply their own corpus and regression harness.

## What's genuinely novel at the code level

1. The `FirmwareStructure` + `Class()` + commit-aware `Struct` triple (`base.py:390-509`, `base.py:650-701`, `base.py:719+`) turns one declarative `construct.Struct` into a class hierarchy where parse / build / JSON / SBOM / text-report / Qt model all derive from a single schema — no parallel byte-walkers, unlike EDK2 or `uefi-firmware-parser`.
2. `CommitMystery` + `MysteryBytes` give graceful degradation on malformed or unknown sub-trees so partial output is always usable for DFIR — a capability missing in most reference implementations.
3. The mypy plugin (`mypy.py`) bridging declarative Construct fields into static types so a ~25k-LOC dynamically-typed parser can ship under `strict = True` is uncommon engineering for a firmware tool.
