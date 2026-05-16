# DFIR (firmware + memory forensics) source mirrors

Git submodules for low-level forensics tools released in early 2026 that remove a long-standing **external-dependency** requirement (vendor SDKs for firmware, debug-symbol packages for memory). See [`../../reports/firmware-memory-forensics.md`](../../reports/firmware-memory-forensics.md) for the deep-dive.

## Layout

| Path | Upstream | Layer | Note |
|---|---|---|---|
| [`cert-uefi-parser/`](./cert-uefi-parser) | https://github.com/cmu-sei/cert-uefi-parser | UEFI firmware | CMU/SEI CERT's NDA-free UEFI ROM / installer / PE parser. Construct-based, extensible. Outputs ASCII / JSON / SBOM-JSON / Qt GUI. **(new 2026)** |
| [`mquire/`](./mquire) | https://github.com/trailofbits/mquire | Linux kernel memory | Trail of Bits' Rust DFIR tool. Analyzes Linux memory snapshots **without external debug symbols**, using kernel-embedded BTF + Kallsyms. SQL shell over kernel data structures. Apache-2.0. **(new 2026)** |

## Cross-list

- The `cert-uefi-support` companion package ([`cmu-sei/cert-uefi-support`](https://github.com/cmu-sei/cert-uefi-support)) provides decompression and binary-utility primitives used by the parser. Install via PyPI; not mirrored separately.
- [`CERTCC/UEFI-Analysis-Resources`](https://github.com/CERTCC/UEFI-Analysis-Resources) is the documentation companion — vendor format notes, EDK2 dev overview, classifications of UEFI vulnerability classes.

## Recent DFIR tools worth knowing about (not mirrored here)

Pattern is identical — ask if you want any added:

- **[Volatility 3](https://github.com/volatilityfoundation/volatility3)** — the cross-OS memory-forensics standard. Profile-dependent; complements `mquire` for environments where symbols are available.
- **[AVML](https://github.com/microsoft/avml)** — Microsoft's recommended Linux memory-acquisition tool. Pairs directly with mquire (don't use `--compress` — mquire reads only uncompressed `.lime`).
- **[LiME](https://github.com/504ensicsLabs/LiME)** — historical memory acquisition; mquire still reads its output format.
- **[btf2json](https://github.com/lolcads/btf2json)** — academic precursor to mquire (BTF for memory forensics).
- **[UEFITool](https://github.com/LongSoft/UEFITool)** — the community-standard interactive UEFI parser; complements CERT UEFI Parser for click-through inspection.
- **[chipsec](https://github.com/chipsec/chipsec)** — Intel's live-system UEFI / chipset analyzer.
- **[fwhunt-scan](https://github.com/binarly-io/fwhunt-scan)** — Binarly's IDA-script-driven firmware scanner.

## Common operations

```bash
git submodule update --init --recursive
git submodule update --remote sources/dfir/mquire
git submodule deinit sources/dfir/<name>
git rm sources/dfir/<name>
rm -rf .git/modules/sources/dfir/<name>
```
