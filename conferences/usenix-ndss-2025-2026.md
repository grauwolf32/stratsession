# USENIX Security '25 & NDSS Symposium 2026

**Academic conferences with released code — combined writeup**

USENIX Security '25 — **Seattle · August 13–15, 2025**
NDSS Symposium 2026 — **San Diego · February 23–27, 2026** (265 papers accepted; **Fuzzing Workshop** co-located Feb 27)

Primary pages:
- USENIX '25 Cycle 1 accepted: https://www.usenix.org/conference/usenixsecurity25/cycle1-accepted-papers
- NDSS 2026 accepted: https://www.ndss-symposium.org/ndss2026/accepted-papers/
- NDSS 2026 program: https://www.ndss-symposium.org/ndss-program/symposium-2026/
- FUZZING'26 workshop: https://fuzzing-workshop.github.io/

---

## USENIX Security '25 — fuzzing-with-code releases

These are the released-code fuzzing papers most directly applicable to AppSec / vuln-research programs.

- **IDFuzz: Intelligent Directed Grey-box Fuzzing** (Yiyang Chen et al.) — Input mutation strategy designed to **complement** most existing state-of-the-art directed fuzzers; drop-in mutation layer for AFL++/Fuzztruction.  
  https://www.usenix.org/conference/usenixsecurity25/presentation/chen-yiyang
- **G²FUZZ** — Outperformed AFL++, Fuzztruction, FormatFuzzer in coverage + bug-finding; 10 unique bugs found in real-world software, 3 confirmed by CVE.
- **Lyso: Multi-target Multi-step Directed Greybox Fuzzing for Static Analysis Verification** (Andrew Bao et al.) — designed to **verify static-analysis findings**; closes the SAST → fuzzing-confirmation loop. https://www.usenix.org/system/files/usenixsecurity25-bao-andrew.pdf
- **GenHuzz: An Efficient Generative Hardware Fuzzer** (Lichao Wu) — Reframes hardware fuzzing as a policy-optimization problem; generates subtler/more-effective test cases. https://www.usenix.org/conference/usenixsecurity25/presentation/wu-lichao
- **MBFuzzer — Multi-Party Protocol Fuzzer for MQTT Brokers** (Xiangpu Song) — Multi-party fuzzing framework with two input senders; targets multi-party communication paths previously hard to fuzz. https://www.usenix.org/system/files/conference/usenixsecurity25/sec25cycle1-prepub-596-song-xiangpu.pdf
- **Robust, Efficient, Widely Available Greybox Fuzzing for COTS Binaries** (Jifan Xiao) — Novel feedback mechanism, **system call pattern coverage**, that supports binaries unhandled by existing approaches — *no binary rewriting, emulators, or Intel-PT needed*. https://www.usenix.org/conference/usenixsecurity25/presentation/xiao-jifan
- **Low-Cost and Comprehensive Non-textual Input Fuzzing with LLM-Synthesized Input Generators** (Kunpeng Zhang) — LLMs generating *generators* (not just inputs) for non-textual format fuzzing.

---

## NDSS 2026 — fuzzing-with-code releases

NDSS 2026: 265 papers (113 summer + 152 fall cycle).

- **Fuzzilicon: A Post-Silicon Microcode-Guided x86 CPU Fuzzer** — Johannes Lenzen, Mohamadreza Rostami, Lichao Wu, Ahmad-Reza Sadeghi (TU Darmstadt). Microcode-guided CPU fuzzing of shipped x86 silicon — first post-silicon microcode-aware fuzzer of its class.
- **DUMPLING: Fine-grained Differential JavaScript Engine Fuzzing** — Liam Wachter, Julian Gremminger, Christian Wressnegger, Mathias Payer, Flavio Toffalini. **8 new bugs** in the heavily-tested V8 engine. https://www.ndss-symposium.org/ndss-paper/dumpling-fine-grained-differential-javascript-engine-fuzzing/
- **IoTBec** — Recurring-vulnerability detection framework deeply integrating signature-based detection with **LLM-driven fuzzing**: LLMs generate targeted payloads for verification of pattern-matched suspicious code. Firmware/source-code-independent.

**FUZZING'26 Workshop** (Feb 27, 2026) co-located with NDSS — community track for academic + industrial fuzzing work; release-quality tooling here usually beats "headline" papers for production AppSec teams. Site: https://fuzzing-workshop.github.io/

---

## How to use academic fuzzer releases

1. **For SAST follow-up** — Lyso pairs directly with whatever SAST stack you run; it's the explicit "confirm or refute static findings" tool of the year.
2. **For COTS / closed-source binaries** — Xiao et al.'s system-call-pattern-coverage feedback removes the historical need for binary rewriting or Intel-PT — large reduction in setup cost for fuzzing third-party binaries.
3. **For protocol / IoT** — MBFuzzer (multi-party MQTT) and IoTBec (LLM-generated firmware payloads) are early but worth piloting against your IoT estate.
4. **For browser-engine adjacent codebases** — DUMPLING's differential approach is generalizable beyond V8 to any spec-compliant runtime.
5. **For mutation strategy** — IDFuzz is the most drop-in option; it's designed to **augment**, not replace, your existing directed fuzzer.

---

## Sources
- USENIX '25 Cycle 1: https://www.usenix.org/conference/usenixsecurity25/cycle1-accepted-papers
- NDSS 2026 accepted: https://www.ndss-symposium.org/ndss2026/accepted-papers/
- NDSS 2026 program: https://www.ndss-symposium.org/ndss-program/symposium-2026/
- FUZZING'26 workshop: https://fuzzing-workshop.github.io/ and https://www.ndss-symposium.org/ndss-program/fuzzing-2026/
- Awesome-fuzzing reference: https://github.com/cpuu/awesome-fuzzing
