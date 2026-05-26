# Fuzzing Research Frontier — USENIX Security '25 & NDSS 2026

This report covers academic fuzzing papers with released code from USENIX Security '25 (Seattle, Aug 13-15, 2025) and NDSS 2026 (San Diego, Feb 23-27, 2026). It is **not** a production-tooling report. For the production fuzzers (AFL++, LibAFL, Ruzzy), see [`fuzzing.md`](./fuzzing.md). For API fuzzing (RESTler, Schemathesis), see [`code/restler-fuzzer.md`](./code/restler-fuzzer.md) and [`code/schemathesis.md`](./code/schemathesis.md). The primary conference listing lives in [`../conferences/usenix-ndss-2025-2026.md`](../conferences/usenix-ndss-2025-2026.md).

These papers matter because they define what production fuzzers will absorb in the next 12-18 months. IDFuzz's mutation strategy will end up as an AFL++ flag. Lyso's SAST-verification loop will become a CI pipeline stage. The pattern is consistent: academic fuzzer papers → prototype code → cherry-picked into AFL++/LibAFL/OSS-Fuzz within two release cycles.

---

## Taxonomy

| Paper | Venue | Target domain | Input type | Feedback mechanism | LLM-assisted? | Bugs reported |
|---|---|---|---|---|---|---|
| IDFuzz | USENIX '25 | Source / binary | Byte-stream | Coverage (directed) | No | Drop-in; inherits host fuzzer's trophies |
| G2FUZZ | USENIX '25 | Source | Structured (file formats) | Coverage + bug oracles | No | 10 unique, 3 CVE-confirmed |
| Lyso | USENIX '25 | Source | Byte-stream | Multi-target directed | No | Confirms/refutes SAST warnings |
| GenHuzz | USENIX '25 | Hardware (RTL) | Stimulus sequences | Policy-optimization reward | No | Hardware design bugs |
| MBFuzzer | USENIX '25 | Protocol (MQTT) | Multi-party messages | Protocol-state coverage | No | MQTT broker bugs |
| Xiao et al. | USENIX '25 | COTS binaries | Byte-stream | Syscall-pattern coverage | No | Binary-only targets |
| Zhang et al. | USENIX '25 | Non-textual formats | Generated generators | Coverage | Yes (generator synthesis) | Format-specific |
| DUMPLING | NDSS '26 | JS engines (V8) | JS programs | Differential (cross-engine) | No | 8 new V8 bugs |
| Fuzzilicon | NDSS '26 | x86 CPUs (post-silicon) | Microcode-guided stimuli | Microcode coverage | No | CPU errata |
| IoTBec | NDSS '26 | IoT firmware | Network payloads | Signature-based recurrence | Yes (payload generation) | Recurring firmware vulns |

Three papers use LLMs (Zhang et al., IoTBec, and indirectly DUMPLING's differential strategy benefits from structured generation). The rest are classical greybox or directed fuzzers with novel feedback signals.

---

## USENIX Security '25 papers

### IDFuzz: Intelligent Directed Grey-box Fuzzing

**Authors:** Yiyang Chen et al.
**Paper:** https://www.usenix.org/conference/usenixsecurity25/presentation/chen-yiyang

**What it does.** IDFuzz is a mutation-strategy layer, not a standalone fuzzer. It plugs into an existing directed greybox fuzzer (AFL++, Fuzztruction) and replaces the mutation scheduler with one that learns which mutations are productive for reaching a specific target location.

**Novelty.** Most directed fuzzers innovate on seed scheduling (which seed to fuzz next) or distance metrics (how to measure progress toward a target). IDFuzz innovates on mutation selection instead -- given a seed, which specific mutation operators are most likely to advance toward the target? This is orthogonal to existing directed-fuzzer improvements, which is why it works as a drop-in complement.

**Practical applicability.** High. The drop-in design means you can layer it on top of whatever directed fuzzer you already run. If you use AFL++ with AFLGo-style directed fuzzing, IDFuzz's mutation strategy is the most natural next upgrade. Expect this to appear as an AFL++ mutator plugin or LibAFL `Mutator` trait implementation within a release cycle.

### G2FUZZ

**What it does.** A structured-input fuzzer that outperformed AFL++, Fuzztruction, and FormatFuzzer in both coverage and bug-finding across file-format targets. Found 10 unique real-world bugs, 3 confirmed by CVE.

**Novelty.** The specific advance is in how it generates structured inputs that satisfy format constraints while still exploring novel code paths. Where FormatFuzzer requires a grammar specification and AFL++ treats inputs as flat byte arrays, G2FUZZ occupies the middle ground: it learns enough structure to be productive without requiring a full format grammar upfront.

**Practical applicability.** Medium-high. If you fuzz file parsers (PDF, image formats, media codecs), G2FUZZ is worth evaluating head-to-head against your current AFL++ setup. The 3 CVE-confirmed bugs demonstrate it finds things AFL++ misses on the same targets. The limitation is the same as all structured fuzzers: setup cost is higher than `afl-fuzz -i corpus -o out -- ./target @@`.

### Lyso: Multi-target Multi-step Directed Greybox Fuzzing for Static Analysis Verification

**Authors:** Andrew Bao et al.
**Paper:** https://www.usenix.org/system/files/usenixsecurity25-bao-andrew.pdf

**What it does.** Takes static-analysis findings (SAST warnings) and attempts to confirm or refute them by fuzzing toward the reported bug locations. Handles multi-step paths where the bug requires reaching multiple program points in sequence.

**Novelty.** This is the first fuzzer explicitly designed to close the SAST-to-confirmation loop. Existing directed fuzzers (AFLGo, Hawkeye, WindRanger) target a single location. Lyso targets multiple locations in a specified order -- exactly what you need to confirm a static-analysis finding like "use-after-free: allocated at line 42, freed at line 87, used at line 103."

**Practical applicability.** Very high for teams running SAST at scale. The perennial SAST problem is false positives: CodeQL / Semgrep / Coverity report findings, and engineers burn time triaging. Lyso converts that triage from "human reads code and guesses" to "fuzzer confirms or times out." The natural integration is: SAST tool emits findings → Lyso consumes findings as fuzzing targets → confirmed findings get filed as bugs, unconfirmed findings get deprioritized. This is a CI pipeline stage waiting to happen.

### GenHuzz: An Efficient Generative Hardware Fuzzer

**Authors:** Lichao Wu
**Paper:** https://www.usenix.org/conference/usenixsecurity25/presentation/wu-lichao

**What it does.** Reframes hardware-design fuzzing (RTL verification) as a policy-optimization problem. Instead of random stimulus generation or manually written test plans, GenHuzz trains a policy that generates stimulus sequences optimized to explore hardware state space.

**Novelty.** The conceptual shift from "coverage-guided search" to "policy optimization" is the contribution. In software fuzzing, coverage feedback is cheap (instrument and run). In hardware fuzzing, simulation cycles are expensive and state spaces are enormous. Framing it as RL-style optimization lets GenHuzz allocate simulation budget more efficiently than coverage-guided approaches.

**Practical applicability.** Narrow but deep. If you do hardware security evaluation (chip design review, FPGA verification), GenHuzz is directly relevant. For software-focused teams, the interest is conceptual: the policy-optimization framing may migrate back to software fuzzing for targets where execution is expensive (full-system emulation, kernel fuzzing, network-service fuzzing with slow round-trips).

### MBFuzzer: Multi-Party Protocol Fuzzer for MQTT Brokers

**Authors:** Xiangpu Song
**Paper:** https://www.usenix.org/system/files/conference/usenixsecurity25/sec25cycle1-prepub-596-song-xiangpu.pdf

**What it does.** Fuzzes MQTT brokers using two input senders simultaneously, targeting multi-party communication paths that single-client fuzzers miss.

**Novelty.** Most protocol fuzzers model a single client-server interaction. MBFuzzer models multi-party communication: two clients publishing and subscribing through a broker, with the fuzzer mutating both streams and their interleaving. This catches bugs triggered by specific message orderings across multiple concurrent connections -- the class of bug that causes real broker outages.

**Practical applicability.** Medium. Directly useful if you run MQTT infrastructure (IoT platforms, industrial control systems, message buses). The multi-party fuzzing concept generalizes to any protocol with pub/sub or multi-client semantics (WebSocket servers, gRPC streaming, database replication protocols), but MBFuzzer itself is MQTT-specific.

### Robust, Efficient, Widely Available Greybox Fuzzing for COTS Binaries

**Authors:** Jifan Xiao
**Paper:** https://www.usenix.org/conference/usenixsecurity25/presentation/xiao-jifan

**What it does.** Provides coverage-guided greybox fuzzing for closed-source binaries using system call pattern coverage as the feedback signal. No binary rewriting, no emulation, no Intel-PT hardware.

**Novelty.** This removes the three historical barriers to binary-only fuzzing: (1) binary rewriting is fragile and architecture-specific, (2) emulators (QEMU) impose 5-20x overhead, (3) Intel-PT requires specific hardware and kernel support. System call patterns are observable on any Linux system via `ptrace` or eBPF, making the approach portable and low-overhead.

**Practical applicability.** Very high. Every security team has COTS binaries they cannot instrument: commercial libraries, legacy services, vendor appliances. Today, fuzzing these requires AFL++ QEMU mode (slow) or FRIDA mode (limited). Xiao et al.'s approach makes binary fuzzing as easy as `strace`-level attachment. The tradeoff is feedback granularity: syscall-pattern coverage is coarser than edge coverage, so it will miss bugs that require fine-grained code-path differentiation. But for the "I have a binary and zero source" use case, coarse feedback that runs at near-native speed beats precise feedback at 10x slowdown.

### Low-Cost and Comprehensive Non-textual Input Fuzzing with LLM-Synthesized Input Generators

**Authors:** Kunpeng Zhang

**What it does.** Uses LLMs to generate input generators (not individual inputs) for non-textual format fuzzing. The LLM writes a program that produces valid-enough inputs for a specific format, and that generator is then used as the seed factory for a conventional coverage-guided fuzzer.

**Novelty.** The meta-level indirection is the key idea. Previous LLM-fuzzing work (FuzzGPT, ChatAFL) uses LLMs to generate individual test inputs, which is expensive per-input and doesn't compose with existing fuzzer mutation. Zhang et al. use the LLM once to generate a generator, then run the generator cheaply at scale. The LLM encodes format knowledge into executable code rather than into individual examples.

**Practical applicability.** Medium-high. The approach is most valuable for formats where writing a grammar is expensive but an LLM can infer the structure from documentation or examples: binary protocols, proprietary file formats, serialization formats. The generated generators serve as seed corpora for AFL++ or LibAFL. This pairs naturally with the Doyensec CFITSIO hybrid workflow (see Cross-references below).

---

## NDSS 2026 papers

### DUMPLING: Fine-grained Differential JavaScript Engine Fuzzing

**Authors:** Liam Wachter, Julian Gremminger, Christian Wressnegger, Mathias Payer, Flavio Toffalini (TU Darmstadt)
**Paper:** https://www.ndss-symposium.org/ndss-paper/dumpling-fine-grained-differential-javascript-engine-fuzzing/

**What it does.** Differential fuzzer for JavaScript engines that found 8 new bugs in V8 -- the most heavily tested JS engine in existence.

**Novelty.** Prior JS-engine differential fuzzers (DIE, Fuzzilli) compare whole-program outputs across engines. DUMPLING operates at finer granularity: it compares intermediate values and execution traces, catching semantic differences that produce the same final output. This is why it finds bugs in V8 that whole-program differentials miss.

**Practical applicability.** Medium. Directly useful if you do browser-engine security research or maintain a JS runtime. For broader applicability, the fine-grained differential technique generalizes to any domain with multiple spec-compliant implementations: database engines (compare query results at the row level, not just final result sets), compilers (compare IR transformations, not just final binaries), cryptographic libraries (compare intermediate state, not just ciphertext).

### Fuzzilicon: A Post-Silicon Microcode-Guided x86 CPU Fuzzer

**Authors:** Johannes Lenzen, Mohamadreza Rostami, Lichao Wu, Ahmad-Reza Sadeghi (TU Darmstadt)

**What it does.** The first post-silicon fuzzer that uses microcode-level guidance to find bugs in shipped x86 CPUs. Operates on real hardware, not RTL simulations.

**Novelty.** Pre-silicon fuzzers (like GenHuzz above) work on design models before tape-out. Fuzzilicon works after the chip ships. It uses microcode update mechanisms and microcode-level coverage signals to guide stimulus generation. This is a fundamentally different threat model: you're testing the actual silicon, including microcode patches and silicon errata that may not be present in design models.

**Practical applicability.** Very narrow. Requires specialized hardware access and microcode expertise. Relevant to CPU vendors, hardware security researchers, and national-security organizations concerned with supply-chain integrity of processors. For everyone else, the academic interest is in the principle: post-deployment fuzzing of hardware, guided by firmware-level coverage, is now demonstrated to be feasible.

### IoTBec: LLM-driven Firmware Fuzzing

**What it does.** Combines signature-based recurring-vulnerability detection with LLM-driven fuzzing for IoT firmware. Identifies known vulnerability patterns in firmware images, then uses LLMs to generate targeted payloads to confirm exploitability.

**Novelty.** The "recurring vulnerability" insight is pragmatic: IoT firmware reuses vulnerable libraries and code patterns across vendors. IoTBec maintains a signature database of known vulnerability patterns and scans firmware for matches. When it finds a match, it doesn't just report it -- it generates LLM-crafted payloads to confirm the bug is triggerable in this specific firmware context. The approach is firmware-independent (no source code required) and source-code-independent.

**Practical applicability.** Medium-high for IoT security teams. The recurring-vulnerability model maps well to how IoT bugs actually manifest: the same `libcurl` overflow appears in 50 different router firmwares with slightly different binary layouts. IoTBec automates the "is this specific firmware instance affected?" confirmation step. Pairs with MBFuzzer for protocol-level coverage of IoT devices.

---

## FUZZING'26 Workshop

Co-located with NDSS, February 27, 2026. Site: https://fuzzing-workshop.github.io/

The workshop track consistently produces more deployment-ready tooling than the main conference. Papers here tend to be shorter, more implementation-focused, and more likely to ship usable code artifacts. Worth monitoring for the next wave of AFL++/LibAFL integrations.

---

## Hybrid fuzz + LLM workflows: the Doyensec reference

Doyensec's "CFITSIO Fuzzing" blog post (April 2026) documents a hybrid workflow combining coverage-guided fuzzing with LLM-assisted harness generation and crash analysis. The result: 16 memory corruption bugs in a single library. This is currently the best public reference write-up for how to combine LLM capabilities with traditional fuzzing infrastructure in practice.

The workflow pattern: LLM generates fuzzing harnesses from library API documentation → conventional fuzzer (AFL++/libFuzzer) runs the harnesses → LLM triages and deduplicates crashes → human confirms. Zhang et al.'s "LLM-synthesized input generators" paper (USENIX '25, above) provides the academic formalization of the first step; Doyensec's write-up provides the practitioner's end-to-end account.

---

## How to use academic fuzzer releases

Adapted from the guidance in [`../conferences/usenix-ndss-2025-2026.md`](../conferences/usenix-ndss-2025-2026.md):

1. **For SAST follow-up** -- Lyso pairs directly with whatever SAST stack you run (CodeQL, Semgrep, Coverity). It is the explicit "confirm or refute static findings" tool. This is the highest-ROI integration on the list.
2. **For COTS / closed-source binaries** -- Xiao et al.'s syscall-pattern-coverage feedback removes the need for binary rewriting or Intel-PT. Large reduction in setup cost for fuzzing third-party binaries.
3. **For protocol / IoT** -- MBFuzzer (multi-party MQTT) and IoTBec (LLM-driven firmware) are early but worth piloting against your IoT estate. Run them together: MBFuzzer for protocol-layer bugs, IoTBec for firmware-layer recurring vulns.
4. **For browser-engine-adjacent codebases** -- DUMPLING's fine-grained differential approach generalizes beyond V8 to any spec-compliant runtime with multiple implementations.
5. **For mutation strategy** -- IDFuzz is the most drop-in upgrade. It augments your existing directed fuzzer, not replaces it.
6. **For file-format fuzzing** -- G2FUZZ is the head-to-head competitor to run against your AFL++ setup on parser targets.
7. **For non-textual formats without grammars** -- Zhang et al.'s LLM-synthesized generators are the lowest-cost way to bootstrap a seed corpus for a novel binary format.

**General guidance for evaluating academic fuzzer code:** expect research-quality build systems, limited documentation, and single-target evaluation scripts. The code is proof-of-concept. The value is in the technique, which you extract and reimplement against your existing fuzzing infrastructure (AFL++ custom mutator API, LibAFL `Mutator`/`Observer`/`Feedback` traits). Do not deploy academic fuzzer code directly in CI; instead, identify which component (mutation strategy, feedback signal, seed scheduling) is novel and integrate that component into your production fuzzer.

---

## Cross-references

| Topic | Report | Relationship |
|---|---|---|
| Production fuzzers (AFL++, LibAFL, Ruzzy) | [`fuzzing.md`](./fuzzing.md) | These papers extend or compete with the production tools |
| API fuzzing (RESTler) | [`code/restler-fuzzer.md`](./code/restler-fuzzer.md) | Complementary: RESTler handles API-layer fuzzing; these papers handle binary/protocol/hardware |
| API fuzzing (Schemathesis) | [`code/schemathesis.md`](./code/schemathesis.md) | Complementary: property-based API testing; different target domain |
| AI vuln research (Buttercup) | [`ai-vuln-research.md`](./ai-vuln-research.md) | Buttercup uses OSS-Fuzz/libFuzzer for its fuzzing layer; these papers represent the next-gen techniques Buttercup-class systems will absorb |
| Conference listing | [`../conferences/usenix-ndss-2025-2026.md`](../conferences/usenix-ndss-2025-2026.md) | Primary paper list and URLs |

The strategic read: **Lyso (SAST verification) and Xiao et al. (binary fuzzing without Intel-PT) are the two papers most likely to change how security teams work in 2026-2027.** Lyso because it converts SAST triage from human labor to automated confirmation. Xiao et al. because it makes binary fuzzing accessible without specialized hardware or emulation overhead. Both address bottlenecks that currently cost teams weeks per quarter.
