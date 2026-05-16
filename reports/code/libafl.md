# LibAFL — code-level analysis

LibAFL v0.16.0 is a Cargo workspace containing **~35 internal crates** plus utility binaries, all driven by a single resolver-2 workspace manifest (`crates/libafl/Cargo.toml` is the main fuzzer-engine crate, **not** `libafl/` as in earlier versions — the layout was flattened under `crates/`).

## 1. Workspace overview

`Cargo.toml:1-25` lists 35 workspace members under `crates/` plus 9 `utils/`. `default-members` (`Cargo.toml:35-41`) ships only the core five: `libafl_bolts`, `libafl_cc`, `libafl_derive`, `libafl_targets`, `libafl`. Notable crate roles:

- `crates/libafl/` — the engine: `inputs/`, `observers/`, `feedbacks/`, `mutators/`, `corpus/`, `executors/`, `schedulers/`, `stages/`, `fuzzer/`, `events/`, `monitors/`, `state/`.
- `crates/libafl_bolts/` — small, dependency-light helpers: `argparse`, `cli`, `compress`, `fs`, `staterestore`, `simd`, `os`. It does **not** contain the LLMP code anymore.
- `crates/ll_mp/` — the standalone LLMP (Low-Latency Message Passing) implementation, a single 3996-line file (`crates/ll_mp/src/lib.rs`).
- `crates/shmem_providers/` — `ShMem` / `ShMemProvider` abstractions and unix-shmem-server.
- `crates/libafl_targets/` — C/Rust glue for harnesses: edges map, sancov PC-guard, cmplog, value-profile, libfuzzer shim, drcov.
- `crates/libafl_cc/` — compiler wrappers and LLVM passes (`autotokens-pass.cc`, `cmplog-instructions-pass.cc`, `cmplog-routines-pass.cc`, `coverage-accounting-pass.cc`, `ctx-pass.cc`, `dump-cfg-pass.cc`, `function-logging.cc`) plus Rust drivers.
- `crates/libafl_qemu/` — full QEMU usermode/systemmode integration with its own `_sys`, `_build`, `_runner`, and `libvharness_sys` sub-crates.
- `crates/libafl_frida/` — Frida Stalker-based binary-only executor (`crates/libafl_frida/src/executor.rs`, `helper.rs`, `coverage_rt.rs`, `cmplog_rt.rs`, `drcov_rt.rs`, plus an `asan/` subdir).
- `crates/libafl_libfuzzer/` — thin Rust façade re-exporting `libfuzzer_sys` (`crates/libafl_libfuzzer/src/lib.rs:116`); the real runtime is the *excluded* `crates/libafl_libfuzzer_runtime/` shipped as a prebuilt `cdylib` and embedded via `include_bytes!(env!("LIBAFL_LIBFUZZER_RUNTIME_PATH"))` (`crates/libafl_libfuzzer/src/lib.rs:138`).
- `crates/libafl_nyx/`, `crates/libafl_intelpt/`, `crates/libafl_tinyinst/`, `crates/libafl_unicorn/` — backend integrations (KVM-Nyx, Intel PT, TinyInst, Unicorn).
- `crates/libafl_asan/` — a custom ASan runtime (`libafl_asan_fuzz`, `libafl_asan_libc`).
- `crates/libafl_sugar/` — a high-level "just fuzz" API exposed to Python via `bindings/pylibafl`.

Note: there is no longer a top-level `libafl_concolic` crate in 0.16 — concolic/cmplog work has been folded into `libafl_targets/src/cmplog.{rs,c}` and the LLVM `cmplog-*-pass.cc` passes.

## 2. Core generic abstractions

LibAFL's design is a tower of generic trait objects. The "shape" of each trait reveals the data flow:

- `pub trait Input: Clone + Serialize + DeserializeOwned + Debug + Hash` with `to_file/from_file/generate_name` (`crates/libafl/src/inputs/mod.rs:82`).
- `pub trait Observer<I, S>: Named` with `pre_exec` / `post_exec` and `pre_exec_child` / `post_exec_child` (the child variants exist so the same observer can run in fork-mode) (`crates/libafl/src/observers/mod.rs:39-79`). The tuple form `ObserversTuple<I, S>: MatchName` enforces name-indexed retrieval (`observers/mod.rs:83`).
- `pub trait Feedback<EM, I, OT, S>: StateInitializer<S> + Named { fn is_interesting(state, manager, input, observers, exit_kind) -> Result<bool> }` (`crates/libafl/src/feedbacks/mod.rs:77-89`). Feedbacks are composed via `CombinedFeedback<A,B,FL>` with `FeedbackLogic` controlling AND/OR semantics.
- `pub trait Mutator<I, S>: Named { fn mutate; fn post_exec }` returning `MutationResult::{Mutated,Skipped}` (`crates/libafl/src/mutators/mod.rs:101-118`); `MutatorsTuple<I, S>: HasLen` powers the stacked-mutator chains.
- `pub trait Stage<E, EM, S, Z> { fn perform(fuzzer, executor, state, manager) }` paired with `Restartable<S>` for crash-recoverable progress tracking (`crates/libafl/src/stages/mod.rs:88-114`).
- `pub trait Corpus<I>: Sized` with the full `add/replace/remove/get/next/prev/first/last/nth/ids` surface — interior mutability via `&RefCell<Testcase<I>>` (`crates/libafl/src/corpus/mod.rs:109-178`).
- `pub trait Executor<EM, I, S, Z> { fn run_target(fuzzer, state, mgr, input) -> Result<ExitKind> }` plus `HasTimeout/SetTimeout` (`crates/libafl/src/executors/mod.rs:128-149`).
- `pub trait Scheduler<I, S>` with `on_add`, `on_evaluation<OT>`, `next`, `set_current_scheduled` (`crates/libafl/src/schedulers/mod.rs:188-221`).
- `pub trait Fuzzer<E, EM, I, S, ST> { fn fuzz_one; fn fuzz_loop; fn fuzz_loop_for }` and the concrete `StdFuzzer<CS, F, IC, IF, OF>` carrying scheduler, feedback, objective, target-bytes converter and input-filter (`crates/libafl/src/fuzzer/mod.rs:244-315`).

Every generic parameter (`I`, `S`, `EM`, `OT`, `Z`) is propagated through the entire stack — no `dyn`, no type erasure on the hot path. Heterogeneous lists are encoded via the external `tuple_list` crate plus a vendored `tuple_list_ex`.

## 3. Executor types

`InProcessExecutor` is a re-export of `GenericInProcessExecutor<EM, H, HB, HT, I, OT, S, Z>` (`crates/libafl/src/executors/inprocess/mod.rs:58`). Its `run_target` increments `state.executions_mut()`, enters the target through `inner.enter_target` (which installs signal handlers for crash interception), runs hooks pre/post, calls `harness_fn.borrow_mut()(input)`, then leaves the target. The 5-second default timeout is hard-coded in `InProcessExecutor::new`.

`ForkserverExecutor<I, OT, S, SHM>` (`crates/libafl/src/executors/forkserver.rs:708`) drives AFL/AFL++-compatible target binaries. Its `Executor::run_target` impl (`forkserver.rs:1521-1542`) converts the input via `fuzzer.convert_to_target_bytes`, runs `pre_exec_child_all` on observers (the *child* variant is used because the actual work happens in the forked child), calls `self.execute_input` which talks to the persistent forkserver over a control pipe, then `post_exec_child_all`. The struct owns the `Forkserver` (`forkserver.rs:713`), the optional shared-memory testcase channel (`map`, `forkserver.rs:715`), and `nix::sys::time::TimeSpec` timeout.

Other executors found: `CommandExecutor<C, HT, I, OT, S, T>` with separate `Executor` impls for `Child` and `Pid` "configurators", `GenericInProcessForkExecutor`, `CombinedExecutor`, `DifferentialExecutor`, `ShadowExecutor`, and `SANDExecutor<E, ET, C, O>`. Timeout is a *trait* (`HasTimeout`/`SetTimeout`), not a wrapper executor.

`QemuExecutor` (`crates/libafl_qemu/src/executor.rs:51`) and `FridaInProcessExecutor` (`crates/libafl_frida/src/executor.rs:34`) are both built **on top of** `StatefulInProcessExecutor` — they wrap the in-process executor, install architecture-specific crash handlers (e.g. `inproc_qemu_crash_handler` at `executor.rs:66`), and inject backend-specific pre/post-exec calls into the harness path.

## 4. Corpus management

The corpus implementations are layered:

- `InMemoryCorpus<I>` — a `Vec`-of-`RefCell<Testcase<I>>` index map with O(1) id lookup (`crates/libafl/src/corpus/inmemory.rs:382-387`).
- `OnDiskCorpus<I>` — testcase metadata in memory, payload on disk; locking via `fs2` (`crates/libafl/src/corpus/ondisk.rs:54-61`).
- `InMemoryOnDiskCorpus<I>` — keeps both, used as the inner of `CachedOnDiskCorpus`.
- `CachedOnDiskCorpus<I>` (`crates/libafl/src/corpus/cached.rs:22-26`) wraps `InMemoryOnDiskCorpus<I>` plus a `RefCell<VecDeque<CorpusId>> cached_indexes` and a `cache_max_len`. `cache_testcase_input` lazily pulls the input off disk and evicts FIFO by zeroing `*borrowed.input_mut() = None;`. Eviction tolerates `try_borrow_mut` failures by re-queuing the id — a subtle protection against deadlock when the evictee is concurrently borrowed.

Power schedules are not a corpus property but a *scheduler* property: `PowerSchedule { base: BaseSchedule, avoid_crash: bool }` (`crates/libafl/src/schedulers/powersched.rs:161`) is consumed by `PowerQueueScheduler<C, O>` and `WeightedScheduler<C, F, O>` (`crates/libafl/src/schedulers/weighted.rs:99`), the latter parametrised over a `TestcaseScore` strategy. The default `StdWeightedScheduler<C, O> = WeightedScheduler<C, CorpusWeightTestcaseScore, O>`. `SchedulerMetadata` lives in `powersched.rs:33` and is attached to each `Testcase` rather than to the corpus container.

## 5. Monitor / EventManager / LLMP

The `Monitor` trait is a single method that renders to the user — `fn display(&mut self, client_stats_manager, event_msg, sender_id)` (`crates/libafl/src/monitors/mod.rs:93-101`). Concrete impls: `NopMonitor`, `SimplePrintingMonitor`, `SimpleMonitor<F>`, plus `disk.rs`, `disk_aggregate.rs`, `prometheus.rs`, `statsd.rs`, `multi.rs`, and a curses-style `tui/`.

The multi-process layer is two-tier: `Monitor` only formats data, while `EventManager` traits (`EventFirer`/`EventRestarter` at `crates/libafl/src/events/mod.rs:439,590`) carry typed events between worker fuzzers. `LlmpEventManager<EMH, I, S, SHM, SP>` (`crates/libafl/src/events/llmp/mod.rs:226`) implements `EventFirer`, `EventRestarter`, `EventReceiver`, `Restorable`, `SendExiting` and `AwaitRestartSafe`.

**LLMP** itself (`crates/ll_mp/src/lib.rs`) is a unidirectional shared-page protocol: each `LlmpSender<SHM, SP>` (`ll_mp/src/lib.rs:964`) owns `out_shmems: Vec<LlmpSharedMap<SHM>>` plus an `unused_shmem_cache` reuse pool; messages are 64-byte-aligned (`LLMP_CFG_ALIGNNMENT`, `ll_mp/src/lib.rs:174`) and pages default to 256 MiB (`LLMP_CFG_INITIAL_MAP_SIZE = 1 << 28`, `ll_mp/src/lib.rs:168`). Senders never block: when a page fills, an `LLMP_TAG_END_OF_PAGE` message is written and the next page is mapped, capped at `LLMP_CFG_MAX_PENDING_UNREAD_PAGES = 3` before back-pressure. The `LlmpBrokerInner` (`ll_mp/src/lib.rs:2192`) holds one outgoing broadcast sender plus a `Vec<LlmpReceiver<SHM, SP>>` — one per client — and tracks listeners separately so the "exit cleanly after N clients" condition ignores them. Clients (`LlmpClient<SHM, SP>` at `ll_mp/src/lib.rs:3593`) bootstrap by connecting to the broker's TCP listener (`_LLMP_BIND_ADDR` "127.0.0.1" by default) and exchanging `ShMemDescription`s; afterwards all traffic is purely shared-memory and lock-free. The `Launcher<'a, CF, MT, SP>` (`crates/libafl/src/events/launcher.rs:132`) spawns one OS process per core and pins it via `core_affinity2`, each running an `LlmpEventManager` pointing at the broker.

## 6. Mutators

The hierarchy is `Mutator<I, S>` (base) → `ComposedByMutations` (associates a `MutatorsTuple`) → `ScheduledMutator<I, S>` which adds `iterations` and `schedule` plus a default `scheduled_mutate` that runs `iterations()` rounds of `mutations_mut().get_and_mutate(idx, ..)` (`crates/libafl/src/mutators/scheduled.rs:73-97`).

Two concrete schedulers ship: `SingleChoiceScheduledMutator<MT>` (one random pick per call) and `HavocScheduledMutator<MT>` which stacks `1 << rand(0..max_stack_pow)` mutations per call — the classic AFL "havoc" pattern.

An example mutation: `BitFlipMutator` (`crates/libafl/src/mutators/mutations.rs:127-152`):

```rust
fn mutate(&mut self, state: &mut S, input: &mut I) -> Result<MutationResult, Error> {
    if input.mutator_bytes().is_empty() {
        Ok(MutationResult::Skipped)
    } else {
        let bit  = 1 << state.rand_mut().choose(0..8).unwrap();
        let byte = state.rand_mut().choose(input.mutator_bytes_mut()).unwrap();
        *byte ^= bit;
        Ok(MutationResult::Mutated)
    }
}
```

This works on **any** `I: HasMutatorBytes` — there is no `BytesInput` coupling. The remaining ~30 byte mutations follow the same shape. Specialised mutator stacks include `mopt_mutator.rs` (MOpt), `gramatron.rs`, `grimoire.rs`, `nautilus.rs`, `token_mutations.rs`, `encoded_mutations.rs`, `unicode/`, `lua.rs`, and `tuneable.rs`.

## 7. `libafl_libfuzzer` — the drop-in libFuzzer replacement

The trick is a **two-crate split**. `crates/libafl_libfuzzer/` is the dependency that user code pulls in (drop-in for `libfuzzer-sys`); it merely re-exports `libfuzzer_sys::*` (`crates/libafl_libfuzzer/src/lib.rs:116`) and declares the C ABI symbol `LLVMFuzzerRunDriver(argc, argv, harness_fn)` as `unsafe extern "C"`. The actual runtime is the *excluded* crate `crates/libafl_libfuzzer_runtime/` (excluded at `Cargo.toml:55`), pre-built as a `cdylib` and shipped as bytes via `include_bytes!(env!("LIBAFL_LIBFUZZER_RUNTIME_PATH"))` (`crates/libafl_libfuzzer/src/lib.rs:138`). This isolation is intentional: the runtime is compiled with different sanitizer/coverage flags than the user's harness, and embedding it as bytes prevents the user's `-fsanitize-coverage` from instrumenting the fuzzer itself.

On the C side, `crates/libafl_targets/src/libfuzzer.c` declares `LLVMFuzzerTestOneInput` as a weak symbol (via the `EXT_FUNC_IMPL` macro), then defines `main` which dispatches to either `libafl_main()` (if the user provided one) or `LLVMFuzzerRunDriver(&argc, &argv, &LLVMFuzzerTestOneInput)`. The Rust shim in `crates/libafl_targets/src/libfuzzer/mod.rs:16-49` simply `extern "C"` declares `LLVMFuzzerTestOneInput` and wraps it in `libfuzzer_test_one_input(buf: &[u8]) -> i32` — that's the call the in-process executor's `harness_fn` ends up making for every mutated input.

The runtime's actual `LLVMFuzzerRunDriver` (`crates/libafl_libfuzzer_runtime/src/lib.rs:605-654`) duplicates `stderr` (via `STDERR_FD_VAR`) so the target can close fd 2 without losing logs, then calls `libafl_targets_libfuzzer_init` (which forwards to the optional user `LLVMFuzzerInitialize`), parses libFuzzer-compatible CLI flags into `LibfuzzerOptions`, and dispatches to `fuzz_single_forking` / `fuzz_many_forking` in `fuzz.rs`. So the libFuzzer ABI is honoured byte-for-byte while the engine underneath is a full LibAFL fuzzer with cmplog, grimoire, dedup-by-stacktrace, TUI, etc.

## 8. `libafl_qemu`

`libafl_qemu` is Linux-only (`#![cfg(target_os = "linux")]`, `crates/libafl_qemu/src/lib.rs:8`) and re-exports `libafl_qemu_sys` (the bindgen'd QEMU). The executor `QemuExecutor<C, CM, ED, EM, ET, H, I, OT, S, SM, Z>` (`crates/libafl_qemu/src/executor.rs:51`) is just a wrapper around `StatefulInProcessExecutor<EM, Emulator<...>, H, I, OT, S, Z>` — the QEMU `Emulator` lives **as the state** of the in-process executor, so every `run_target` invocation goes through a single, in-process emulator instance rather than forking.

Crash routing is custom: `inproc_qemu_crash_handler` (`executor.rs:66`) is installed in place of the default in-process handler so that signals delivered inside QEMU's translated code (rather than native LibAFL code) are correctly attributed to the testcase. `systemmode` adds `BREAK_ON_TMOUT: AtomicBool` and `libafl_exit_request_timeout` calls because in system mode you can't just `setitimer` the host — you have to ask QEMU to break out of its TCG block dispatch loop.

Instrumentation is exposed via the `EmulatorModule<I, S>` trait (`crates/libafl_qemu/src/modules/mod.rs:87`) with `first_exec` / `pre_exec` / `post_exec` hooks and a tuple `EmulatorModuleTuple`. Coverage is one such module: `EdgeCoverageModule<AF, PF, V, IS_CONST_MAP, MAP_SIZE>` (`modules/edges/mod.rs:118`) carries an `AddressFilter`, a `PageFilter` (only used in systemmode), and a `use_jit: bool`. In `first_exec` it picks one of four QEMU-side instrumentation strategies (`{jit,fn} × {hitcount, no_hitcount}`) by calling into the `EdgeCoverageVariant` trait — JIT variants compile the edge-update sequence into TCG ops, function variants register a host-side callback per translated edge. Edges are written into the same `EDGES_MAP` that `libafl_targets` uses (`crates/libafl_targets/src/coverage.rs:91`, `sancov_pcguard.rs:22`), so any `MapFeedback` works unchanged regardless of whether the backend is sancov, forkserver, Frida, or QEMU.

## 9. What's genuinely novel at the code level

(1) **Total generic monomorphisation with zero `dyn`**: every executor/feedback/scheduler decision is resolved at compile time through deeply-nested generic parameters and `tuple_list` heterogeneous lists (`executors/inprocess/mod.rs:76-83`, `feedbacks/mod.rs:77`), eliminating vtable dispatch from the fuzzing hot loop — something AFL++ achieves only via macros and function-pointer indirection. (2) **The libfuzzer-replacement two-crate split with `include_bytes!`-embedded prebuilt runtime** (`crates/libafl_libfuzzer/src/lib.rs:138`, runtime crate excluded from the workspace at `Cargo.toml:55`) lets LibAFL ship a binary-compatible libFuzzer drop-in that cannot be cross-instrumented by the user's sanitizer flags. (3) **A single unified edges-map** (`crates/libafl_targets/src/coverage.rs`) shared across forkserver, in-process sancov, QEMU TCG/JIT (`modules/edges/mod.rs`) and Frida Stalker (`libafl_frida/src/coverage_rt.rs`) means a `MapFeedback` written once works against every backend — the abstraction boundary is the `u8[MAP_SIZE]` byte buffer, nothing higher-level.
