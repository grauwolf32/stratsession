# Fuzzing — AFL++ · LibAFL · Ruzzy

All three are from the same lineage (`AFLplusplus` org + Trail of Bits), but they answer different questions. **AFL++ is a polished product**, **LibAFL is a library**, **Ruzzy is a niche-language coverage-guided fuzzer**. Reading them together shows what "modern fuzzing" looks like in 2026.

| | AFL++ | LibAFL | Ruzzy |
|---|---|---|---|
| Language | C | Rust | Ruby (C bridge) |
| Form factor | Fuzzer binary (`afl-fuzz`) | Library of building blocks | Ruby gem |
| Primary mode | Greybox / coverage-guided | Build your own fuzzer | Coverage-guided libFuzzer wrapper |
| Inspiration | Forked from Google's AFL | Designed from scratch | Inspired by Google's Atheris (Python) |
| Scope | Native binaries | Anything (no_std capable) | Ruby + Ruby C extensions |
| Maturity | v4.40c, dominant in industry | v0.15.x, academic + library-first | v0.8.x, niche but real |
| Repo size | 16 MB | 35 MB | 204 KB |

## What's actually novel in each

### AFL++ — the "best-of" fuzzer

AFL++ is not novel as a *concept*; it's novel as an *integration*. It's an opinionated fork of AFL that bolts in the best ideas from a decade of fuzzing research, all behind a single `afl-fuzz` interface. The headline feature matrix from `docs/features.md` is unusually concrete:

- **CmpLog instrumentation** — AFL++'s evolution of [Redqueen](https://www.ndss-symposium.org/ndss-paper/redqueen-fuzzing-with-input-to-state-correspondence/) (NDSS '19): use comparison operands as hints for mutation. Available across LLVM, GCC, FRIDA, QEMU, Unicorn.
- **LAF-Intel / CompCov** — splits multi-byte comparisons into 8-bit comparisons so coverage instrumentation can incrementally reward bytes that match a known constant. Effectively makes magic-number / token-matching code reachable by mutation.
- **NeverZero counters** — when a coverage counter wraps from 255 to 0, AFL++ skips 0 and goes to 1. Empirically increases coverage discrimination.
- **Non-colliding coverage (PCGUARD)** — vanilla AFL hashes edges into a fixed-size bitmap; AFL++ uses an LTO pass to give each edge a unique slot.
- **Auto-dictionary** — LTO mode extracts constants from comparisons at compile time and feeds them back as dictionary tokens. Fully automatic.
- **MOpt mutator** — particle-swarm-optimized mutation operator selection.
- **AFLfast power schedules** — Marcel Böhme's seed-prioritization model.
- **Persistent mode + shared-memory test cases** — kills the per-execution fork overhead; 10x+ throughput on suitable targets.
- **Instrumentation backends**: LLVM, GCC plugin, FRIDA (binary-only on Linux + macOS, x86/arm64), QEMU (full-system + user-mode), Unicorn (cross-arch emulation), Nyx (x86_64 snapshot-based), Coresight (AArch64 hardware tracing).

The novelty here is the *unifying glue*: each one of those features is a separate research paper, and AFL++ ships them all with consistent flags and `AFL_LLVM_*` environment variables. *Most of the fuzzing literature since 2020 is implementable as an AFL++ flag flip.*

### LibAFL — the "build your own fuzzer" framework

LibAFL is the same team's answer to a different question: *what if you don't want a fuzzer, you want to assemble one?* The repository is a collection of Rust crates that decompose the fuzzer into reusable pieces:

- **`libafl`** core (observers, feedbacks, mutators, schedulers, stages, corpus, state, events)
- **`libafl_cc`** — wraps a C compiler to inject instrumentation (multiple passes available)
- **`libafl_targets`** — common target-side runtime (SanitizerCoverage, ASan hooks, etc.)
- **`libafl_frida`** — binary-only fuzzing via Frida instrumentation
- **`libafl_qemu`** — full-system + user-mode QEMU fuzzing with emulation hooks
- **`libafl_tinyinst`** — TinyInst instrumentation backend
- Multiple per-target example fuzzers in `fuzzers/`

Architecturally novel ideas:

- **Low Level Message Passing (LLMP)** — a custom IPC system that scales nearly linearly across cores and tunnels over TCP across machines. This is the trick behind "120k execs/sec in frida-mode on a phone (all cores)" from the README.
- **`no_std` compatible** — LibAFL can be embedded into kernels, hypervisors, and bare-metal targets. It will run in environments that have no allocator, no thread support, no libc. This is unique in the fuzzer ecosystem.
- **Generic over `Input`** — `BytesInput` is just one possible input shape. You can plug in AST inputs, grammar-derived inputs, or any structured type for "structured fuzzing." The mutators and corpus are generic over your input type at compile time.
- **Generic over `Observer`** — coverage feedback is one observer; you can add custom feedback signals (e.g., binary diff coverage, latency, semantic signals).
- **Compile-time configuration** — most performance-critical decisions are template parameters resolved at compile time rather than runtime polymorphism. Hence the "we do everything we can at compile time" line.

In summary: AFL++ is the *product*, LibAFL is the *toolkit you would have used to build AFL++ if you were starting today*. Both are maintained by overlapping authors (Fioraldi, Maier, et al.). The CCS '22 paper (`@libafl` BibTeX) is the academic publication.

### Ruzzy — fuzzing Ruby (and Ruby C extensions)

Ruzzy is the *narrow but interesting* one. The fuzzing world has rich tooling for C/C++ and increasingly for Rust, but managed languages are spotty. Atheris (Google) covers Python; Jazzer (Google / Code Intelligence) covers JVM. Ruby had patchy tooling: `kisaten`, `afl-ruby`, `FuzzBert` — see the "Further reading" list at the bottom of the README. Ruzzy is the first Atheris-equivalent for Ruby.

What makes Ruzzy interesting beyond filling that gap:

- **libFuzzer as the engine, not AFL** — Ruzzy reuses libFuzzer's coverage + mutation engine directly via SanitizerCoverage. This is the same architectural choice Atheris made for Python.
- **Two-mode fuzzing**:
  - **Pure Ruby fuzzing**: requires a `tracer.rb` and a `harness.rb`. The tracer script is the workaround for "an implementation detail of the Ruby interpreter" — Ruby's bytecode VM doesn't expose coverage in a way libFuzzer can directly consume, so Ruzzy adds a tracing layer.
  - **Ruby C-extension fuzzing**: the C extension is compiled with `-fsanitize=address,fuzzer-no-link`, then linked against Ruzzy's libFuzzer wrapper, with `LD_PRELOAD` injecting ASan first (the same pattern Atheris pioneered).
- **`FuzzedDataProvider`** — a Ruby port of the libFuzzer FDP idiom, with `consume_int_in_range`, `consume_float_in_range`, `pick_value_in_list`, etc. Lets you build structured inputs from raw fuzzer bytes inside Ruby.
- **Trophy case** is non-trivial: a Ruby Marshal GC crash, a REXML/Nokogiri parser differential that became a [GitHub SAML SSO bypass](https://github.blog/security/sign-in-as-anyone-bypassing-saml-sso-authentication-with-parser-differentials/), bugs in `toml`/`toml-rb`/`ox`. Worth showing this to anyone who claims "managed-language fuzzing isn't worth the effort."
- **Academic backing** — Trail of Bits published a paper at the [ACM SCAM '24 workshop](https://dl.acm.org/doi/10.1145/3675741.3675749) on the design.

## Comparison: when to use which

| If you have… | Use | Why |
|---|---|---|
| A C/C++/Rust target and want to fuzz today | AFL++ | Ship-quality, hundreds of features, the fuzzbench reference. |
| Need to fuzz a binary you don't have source for | AFL++ FRIDA mode (or QEMU mode) | Mature binary-only paths. |
| Need to fuzz on weird hardware (hypervisor, kernel module, no_std) | LibAFL | Only fuzzer that builds for `no_std` and embedded. |
| Need a fuzzer with *custom input semantics* (AST/grammar/IR) | LibAFL | Generic over `Input` type. |
| Need to scale fuzzing across many machines | LibAFL | LLMP IPC scales over TCP. |
| Want to fuzz Ruby code or Ruby C extensions | Ruzzy | Only OSS tool in this niche. |
| Want to fuzz Python | Atheris (out of scope for this repo) | Ruzzy's design ancestor. |
| Want to fuzz JVM | Jazzer (out of scope) | The Atheris-equivalent for Java/Kotlin. |

## Strategic read

AFL++ and LibAFL are the *same maintainer team writing the same idea twice* — once as a product and once as a library. The community is iterating on both. If you want to bring AI-assisted fuzzing into your pipeline (CmpLog with LLM-guided dictionary, MOpt with LLM-tuned schedules, etc.), the natural integration surface is **LibAFL**, because its observer/feedback abstraction is where new signals belong. The current Buttercup CRS (see [`ai-vuln-research.md`](./ai-vuln-research.md)) uses OSS-Fuzz + libFuzzer for the actual fuzzing layer — not LibAFL — but that's a deployment-pragma choice, not a technical limit. Expect AIxCC follow-on tooling to land more LibAFL-shaped extensions.

Ruzzy is the right reference design for "I want to add coverage-guided fuzzing to language X" — its tracer+harness pattern + FDP API generalize.
