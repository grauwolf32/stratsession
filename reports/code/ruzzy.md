# Ruzzy — code-level analysis

Ruzzy is a small Ruby gem (~700 LoC across Ruby + C, no Rust) that bridges MRI Ruby into a libFuzzer-compatible runtime. The runtime can be either Clang's stock `libclang_rt.fuzzer_no_main.a` or LibAFL's drop-in `libFuzzer.a` — both are linked through the same `LLVMFuzzerRunDriver` entry point, so the Ruby/C glue is identical for either backend.

## 1. Architecture overview

Two layers:

- **Ruby side** (`lib/ruzzy.rb`) — exposes `Ruzzy.fuzz(proc, argv)` and `Ruzzy.trace(harness)`, holds the `argv` plumbing for libFuzzer re-exec (`lib/ruzzy.rb:14-18`), and monkey-patches `Integer` comparison/division operators so pure-Ruby comparisons feed into SanitizerCoverage (`lib/ruzzy.rb:62-130`).
- **Native side** (`ext/cruzzy/cruzzy.c`) — a Ruby C extension that (a) registers a libFuzzer test-one-input callback that calls back into a stored Ruby proc, (b) re-exports SanCov tracing intrinsics to Ruby (`c_trace_cmp8`, `c_trace_div8`), and (c) attaches an MRI event hook for branch-coverage events that fills an 8-bit counters table SanCov can read.

The fuzzer loop is owned by libFuzzer (`LLVMFuzzerRunDriver`, declared `extern` in `ext/cruzzy/cruzzy.c:24-28`). Ruzzy hands it a C trampoline (`proc_caller`, `ext/cruzzy/cruzzy.c:86-108`) that marshals a `const uint8_t *` into a Ruby `String` and invokes the user's harness proc via `rb_proc_call`.

## 2. Module / package layout

There is no `bin/` or `examples/` directory; harnesses live in `test/`.

- `lib/ruzzy.rb` — public API + `Integer` patch.
- `lib/ruzzy/fuzzed_data_provider.rb` — pure-Ruby port of libFuzzer's `FuzzedDataProvider.h` (`lib/ruzzy/fuzzed_data_provider.rb:28-220`).
- `ext/cruzzy/cruzzy.c` + `ext/cruzzy/extconf.rb` — the real C extension and its sanitizer-archive build glue.
- `ext/dummy/dummy.c` + `ext/dummy/extconf.rb` — a deliberately-buggy second extension used by the smoke test (`Ruzzy.dummy`).
- `test/harness_branch.rb`, `harness_cmp.rb`, `harness_div.rb` — the harnesses that double as `examples/` (the gemspec ships only `lib/` and `ext/`, see `ruzzy.gemspec:9`).
- `entrypoint.sh` — wrapper that sets `LD_PRELOAD=$ASAN_PATH` and `RUZZY_ARGV0=$SCRIPT_PATH` before `require "ruzzy"` (`entrypoint.sh:5-6`).
- `Dockerfile` (stock clang libFuzzer) and `Dockerfile.LibAFL` (LibAFL's `libafl_libfuzzer_runtime` built in stage 1, dropped at `/usr/lib/libFuzzer.a`, then `FUZZER_NO_MAIN_LIB=...` switches the gem build to it — `Dockerfile.LibAFL:36-77`).

## 3. Ruby C extension (`ext/cruzzy/`)

Entry point is `Init_cruzzy` (`ext/cruzzy/cruzzy.c:236-249`), which installs a SIGINT handler that bypasses libFuzzer's own atexit (`graceful_exit` / `ruzzy_exit`, `ext/cruzzy/cruzzy.c:62-84`) and registers five module functions on the existing `Ruzzy` Ruby module:

```c
rb_define_module_function(ruzzy, "c_fuzz",                &c_fuzz,                2);
rb_define_module_function(ruzzy, "c_libfuzzer_is_loaded", &c_libfuzzer_is_loaded, 0);
rb_define_module_function(ruzzy, "c_trace_cmp8",          &c_trace_cmp8,          2);
rb_define_module_function(ruzzy, "c_trace_div8",          &c_trace_div8,          1);
rb_define_module_function(ruzzy, "c_trace",               &c_trace,               1);
```

`c_libfuzzer_is_loaded` (`ext/cruzzy/cruzzy.c:45-58`) is a clever sanity check — it `dlopen(NULL)`s the running process and `dlsym`s `LLVMFuzzerRunDriver` to verify the user actually `LD_PRELOAD`ed the merged ASan+libFuzzer .so before calling `Ruzzy.fuzz`.

The build (`ext/cruzzy/extconf.rb:40-78`, `116-142`) does something subtle: it can't just link `libclang_rt.asan.a` and `libclang_rt.fuzzer_no_main.a` because both define `_preinit` symbols that collide with Ruby's own startup. So `merge_sanitizer_libfuzzer_lib` copies the sanitizer archive, `ar d`'s the `asan_preinit.cc.o` / `asan_preinit.cpp.o` members out, then `--whole-archive`-links the result with libFuzzer into a single `asan_with_fuzzer.so` that's safe to `LD_PRELOAD` (the comment cites Atheris's `native_extension_fuzzing.md` as prior art at `ext/cruzzy/extconf.rb:41`). Same trick for UBSan (`ext/cruzzy/extconf.rb:136-142`).

## 4. MRI Ruby coverage hook

Ruzzy uses three orthogonal signals into SanitizerCoverage:

1. **Branch coverage via `RUBY_EVENT_COVERAGE_BRANCH`.** The constant `0x020000` is hardcoded in `cruzzy.c` because Ruby's header keeps it internal (`ext/cruzzy/cruzzy.c:12-16`). `c_trace` calls `rb_add_event_hook2(event_hook_branch, RUBY_EVENT_COVERAGE_BRANCH, counter_hash, RUBY_EVENT_HOOK_FLAG_SAFE | RUBY_EVENT_HOOK_FLAG_RAW_ARG)` (`ext/cruzzy/cruzzy.c:220-229`). Critically the comment at `ext/cruzzy/cruzzy.c:195-211` documents a non-obvious initialization order: the hook fires nothing until `Coverage.start(branches: true)` is called from C (`rb_require("coverage")` → `rb_funcall(coverage_mod, rb_intern("start"), ...)`), because `rb_set_coverages` is what actually wires up the interpreter's coverage state.

2. **The hook callback `event_hook_branch`** (`ext/cruzzy/cruzzy.c:176-193`) keys each branch on `(rb_intern_str(path), lineno)`, looks the tuple up in a Ruby `Hash` (`counter_hash`), assigns the next free slot in the `COUNTERS[8192]` table on first sight, and increments `COUNTERS[index % MAX_COUNTERS]++`. That counters table was registered with libFuzzer up front via `__sanitizer_cov_8bit_counters_init(COUNTERS, COUNTERS + MAX_COUNTERS)` plus a dummy PC table (`ext/cruzzy/cruzzy.c:217-218`, `MAX_COUNTERS=8192` at `ext/cruzzy/cruzzy.c:22`). So Ruby branch hits look like 8-bit SanCov counters to libFuzzer.

3. **CmpLog / DivLog via the `Integer` monkey-patch.** `lib/ruzzy.rb:62-130` aliases the original `==`, `===`, `eql?`, `<=>`, `<`, `<=`, `>`, `>=`, `/`, `div`, `divmod` and wraps each one to call `Ruzzy.c_trace_cmp8(self, other)` or `Ruzzy.c_trace_div8(other)` first, then dispatch the original. `c_trace_cmp8` (`ext/cruzzy/cruzzy.c:152-165`) guards on `FIXNUM_P` (no bignum/float support — sancov tops out at 8-byte ints) and forwards into `__sanitizer_cov_trace_cmp8`. Same shape for `__sanitizer_cov_trace_div8` at `ext/cruzzy/cruzzy.c:167-174`.

## 5. LibAFL integration

There is no Rust in this repo — Ruzzy's only LibAFL integration is the ABI-compatible swap of the libFuzzer runtime archive. The `Dockerfile.LibAFL` build clones LibAFL, runs `crates/libafl_libfuzzer_runtime/build.sh --cargo-args "--no-default-features --features no_link_main"` (`Dockerfile.LibAFL:36-38`), and copies the resulting `libFuzzer.a` into the runtime image. The gem build then picks it up via `FUZZER_NO_MAIN_LIB=/usr/lib/libFuzzer.a` (`Dockerfile.LibAFL:77`, consumed in `ext/cruzzy/extconf.rb:23` and `ext/cruzzy/extconf.rb:81-102`).

Because `libafl_libfuzzer_runtime` exposes the same `LLVMFuzzerRunDriver` + SanCov symbol surface that clang's libFuzzer does, no other code changes are needed — the `extern` declaration at `ext/cruzzy/cruzzy.c:24-28` and the `__sanitizer_cov_*` calls bind to whichever runtime got `--whole-archive`'d into the merged `.so`.

A worth-noting comment at `ext/cruzzy/cruzzy.c:21-22`: `MAX_COUNTERS = 8192`, "should we mmap like Atheris?" — meaning the counters table is a fixed BSS array, not a sized-at-runtime shared mapping. With LibAFL's runtime that's the same map-size cap.

## 6. Harness pattern

Harnesses are written as a lambda + a `Ruzzy.fuzz` call. The cmp harness shows the pure-Ruby path:

```ruby
# test/harness_cmp.rb:5-19
test_one_input = lambda do |data|
  if data.unpack1('H*').to_i(16) == 'FUZZ'.unpack1('H*').to_i(16)
    raise 'TEST HARNESS CMP'
  end
  0
end

Ruzzy.fuzz(test_one_input, ['ruzzytestprogname',
                            '-max_total_time=30',
                            "-exact_artifact_path=#{File::NULL}"])
```

The `Integer#==` patch makes the multibyte comparison observable to SanCov so libFuzzer's CmpLog mutator can solve it (`lib/ruzzy.rb:76-79`). The `harness_branch.rb` and `harness_div.rb` files exercise the branch-hook and div-by-zero paths the same way. The C-extension path is the `Ruzzy.dummy` flow: `lib/ruzzy.rb:33-40` does `require 'dummy/dummy'` (loading the ASan-instrumented `.so`) *after* the wrapper has set `LD_PRELOAD`, then calls `Ruzzy.fuzz(->(data) { dummy_test_one_input(data) })`, which lets the proc trampoline into the C `_c_dummy_test_one_input` containing an intentional heap-use-after-free (`ext/dummy/dummy.c:7-25`).

`FuzzedDataProvider` is positioned for structured harnesses (`lib/ruzzy/fuzzed_data_provider.rb:18-27` shows the canonical pattern: front-cursor for strings, back-cursor for ints — a faithful port of libFuzzer's bidirectional consumption model — see `consume_int_in_range` at `lib/ruzzy/fuzzed_data_provider.rb:128-150` and `pick_value_in_list` at `lib/ruzzy/fuzzed_data_provider.rb:198-202`).

## 7. Persistent vs fork mode

Ruzzy runs **in-process persistent mode by default** — `LLVMFuzzerRunDriver` repeatedly calls `proc_caller` (`ext/cruzzy/cruzzy.c:86-108`) without forking. `PROC_HOLDER` is a global `VALUE` (`ext/cruzzy/cruzzy.c:43`) that pins the user's lambda for the lifetime of the run. There is no per-iteration `rb_protect`; an uncaught Ruby exception escapes into libFuzzer, which treats it as a crash.

MRI forking is heavy, so Ruzzy avoids it for the hot loop. It does have to *tolerate* libFuzzer's own re-exec, though: libFuzzer's `-merge=1` and `-fork=N` modes `system(argv[0] ...)` to spawn workers. Because `argv[0]` would normally be `ruby`, the wrapper script in `entrypoint.sh:3-6` advertises its own path via `RUZZY_ARGV0`, which `lib/ruzzy.rb:10-15` propagates into the `argv[0]` slot of `DEFAULT_ARGS`. So re-execution goes through `entrypoint.sh` again, re-applying `LD_PRELOAD=$ASAN_PATH`. The test harness itself uses MRI `fork` (`test/test_ruzzy.rb:24-43`) only as a test-isolation technique — each test fork runs one fuzz session, gets killed, and the parent inspects its output and the libFuzzer artifact file.

## 8. Crash dedup and corpus management

Ruzzy does not implement either — both are delegated to libFuzzer. The user passes raw libFuzzer flags through the `args` array; the test harnesses use `-exact_artifact_path=#{File::NULL}` to suppress crash artifacts (`test/harness_branch.rb:25`) or `-exact_artifact_path=<tempfile>` to capture exactly one (`test/test_ruzzy.rb:54`). Crash files are libFuzzer's standard SHA1-named `crash-<hash>` artifacts.

The one Ruzzy-specific touch is exit handling: `proc_caller` returns `0` on `nil` so users don't have to remember to `return 0` from their harness (`ext/cruzzy/cruzzy.c:95-98`, with a libFuzzer "Rejecting unwanted inputs" reference in the comment), and `graceful_exit` (`ext/cruzzy/cruzzy.c:67-73`) registers an atexit that calls `_exit` directly, suppressing libFuzzer's own at-exit reporting so SIGINT produces a clean shutdown rather than a fake crash report.

## 9. What's genuinely novel at the code level

The bridge itself is the contribution: a ~250-line C extension that turns Ruby's `RUBY_EVENT_COVERAGE_BRANCH` event hook into a SanitizerCoverage 8-bit-counters table (`ext/cruzzy/cruzzy.c:176-234`) and then re-exposes `__sanitizer_cov_trace_cmp8` / `__sanitizer_cov_trace_div8` as Ruby methods that get wired in via an `Integer` monkey-patch (`lib/ruzzy.rb:62-130`). That's the trick — pure Ruby comparisons feed CmpLog with no Ruby VM changes, and the same C extension binary runs on either clang's libFuzzer or LibAFL's `libafl_libfuzzer_runtime` because the integration is purely at the `LLVMFuzzerRunDriver` + SanCov ABI boundary (`ext/cruzzy/cruzzy.c:24-33`, `Dockerfile.LibAFL:36-77`). The sanitizer-archive surgery in `extconf.rb` (`ext/cruzzy/extconf.rb:40-78`) — `ar d`'ing the duplicate preinit objects so ASan can coexist with Ruby's startup in a single `LD_PRELOAD` — is the kind of build-system detail that's the actual reason this niche has been empty for a decade.
