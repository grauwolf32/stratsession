# Buttercup — code-level analysis

## 1. Architecture overview

Buttercup is a collection of Python "bot" processes that share **nothing but a Redis instance** and a host-mounted scratch volume. There is no gRPC, no direct service-to-service HTTP, and no Kubernetes API usage between components — all coordination is **Redis Streams + protobuf payloads**. The contract is in a single `.proto` (`common/protos/msg.proto`) defining 14 messages (`Task`, `BuildRequest`, `BuildOutput`, `Crash`, `TracedCrash`, `ConfirmedVulnerability`, `Patch`, `POVReproduceRequest/Response`, `SubmissionEntry`, `Bundle`, …) and the queue/group catalogue is hard-coded in `common/src/buttercup/common/queues.py:38-60`.

The reliability layer is custom: `ReliableQueue` in `queues.py:99-212` wraps `XADD` / `XREADGROUP` / `XACK` and, critically, calls `XAUTOCLAIM` (line 166) whenever a consumer finds its pending list empty — so any worker pod that died with an un-acked message has its work re-claimed after a per-queue `task_timeout_ms` (e.g. 15 min for builds, 10 min for downloads — `queues.py:66-80`). This is what lets every bot be a plain `Deployment` with no leader-election: at-least-once delivery is the entire HA story.

Large artefacts (built fuzz targets, corpus directories, CodeQuery DBs) don't fit in Redis, so a `node_local` helper (`common/src/buttercup/common/node_local.py:138-232`) tars them into a shared remote-archive path on first emit and untars on first consume — i.e. **content-addressed gzip-on-shared-volume** is the data plane, Redis is only the control plane.

## 2. Module / package layout

Eight top-level Python packages, each its own `pyproject.toml` and Dockerfile:

| Dir | Bot(s) it produces | Role |
|-----|---|---|
| `common/` | (library) | protobuf + Redis queues + `ChallengeTask` OSS-Fuzz wrapper |
| `orchestrator/` | `scheduler`, `downloader`, `task-server`, `pov-reproducer`, `scratch-cleaner`, `ui` | brain + REST ingest + submission state machine |
| `fuzzer/` | `builder-bot`, `fuzzer-bot`, `coverage-bot`, `tracer-bot`, `merger-bot` | ClusterFuzz-driven libFuzzer/AFL/Jazzer execution |
| `fuzzer_runner/` | (subprocess called by fuzzer) | thin subprocess wrapper around `clusterfuzz.fuzz.get_engine()` |
| `program-model/` | `program-model` | CodeQuery + tree-sitter indexer |
| `seed-gen/` | `seed-gen` | LangGraph LLM agent that writes Python seed-generators |
| `patcher/` | `patcher` | LangGraph multi-agent patch generator |
| `litellm/` | LiteLLM proxy | model routing/rate-limiting |
| `deployment/` | Helm charts | one chart per bot in `k8s/charts/` |

There are no per-language sub-packages — C/C++ and Java are handled by branching on `ProjectYaml.unified_language` everywhere (e.g. `seed-gen/src/buttercup/seed_gen/vuln_base_task.py:361-379`).

## 3. Orchestrator

The "orchestrator" is actually four cooperating bots, but only the **Scheduler** is the central coordinator (`orchestrator/src/buttercup/orchestrator/scheduler/scheduler.py`). Its `serve_item()` (line 437-455) is a single-threaded round-robin over seven sub-actions:

```
cancellation.process_cancellations
update_cached_cancelled_ids
serve_ready_task         # READY_TASKS  → emit IndexRequest + N BuildRequests
serve_build_output       # BUILD_OUTPUT → either register harness for fuzzing or feed Submissions
serve_index_output       # INDEX_OUTPUT → just ack
update_expired_task_weights
competition_api_interactions   # drains TRACED_VULNERABILITIES + PATCHES → submit
```

For each ready task the Scheduler chooses an engine (`libfuzzer` preferred, falling back to `afl`, `scheduler.py:169`), then queues one COVERAGE build, one FUZZER build per sanitizer, and (for delta-mode tasks with diffs) a TRACER_NO_DIFF build.

The actual **state machine** lives in `orchestrator/src/buttercup/orchestrator/scheduler/submissions.py`. `Submissions.process_cycle()` (line 1751-1813) iterates every `SubmissionEntry` stored in Redis and runs ten conditional helpers in a fixed order inside a single Redis pipeline:

1. `_confirm_matched_sarifs`
2. `_ensure_sarif_is_bundled`
3. `_ensure_patch_is_bundled`
4. `_update_patch_status`
5. `_request_patch_if_needed`     ← pushes to `CONFIRMED_VULNERABILITIES`
6. `_request_patched_builds_if_needed` ← pushes `BuildRequest{type=PATCH}` (line 1040-1091)
7. `_submit_patch_if_good`
8. `_update_pov_status`
9. `_submit_pov_if_needed`
10. `_ensure_single_bundle`

After the per-entry loop, `_merge_entries_by_patch_mitigation()` consolidates duplicate vulnerabilities that turn out to be fixed by the same patch. The state is serialised back to Redis on every change (`_persist`, line 735). **This is "the brain" — everything else is a worker.**

## 4. Seed Generator + Fuzzer (the discovery half)

The fuzzer wrapper is **OSS-Fuzz's ClusterFuzz** engine library, not a direct AFL or libFuzzer integration. `fuzzer_runner/src/buttercup/fuzzer_runner/runner.py:30-51` literally calls `clusterfuzz.fuzz.get_engine(conf.engine).prepare(...).fuzz(...)` and returns a `FuzzResult` — so the same binary handles libfuzzer, afl, honggfuzz, and centipede transparently. `FuzzerBot.run_task` (`fuzzer/src/buttercup/fuzzing_infra/fuzzer_bot.py:55-139`) wraps that with: pull a `WeightedHarness` task → pick a random FUZZER build → run a single fuzzing campaign → for every unique crash (deduplicated by stack-trace token via `CrashSet`, line 113-126) push a `Crash` protobuf onto `QueueNames.CRASH`.

The seed-gen integration point is **the corpus directory on shared storage** — not the queue. `SeedGenBot.run_task` (`seed-gen/src/buttercup/seed_gen/seed_gen_bot.py:124-257`) randomly picks one of three LangGraph workflows (`seed-init` / `vuln-discovery` / `seed-explore`, weighted at 5/35/60% for full-mode and 5/45/50% for delta-mode), each of which ends by writing files to `out_dir` and then `corp.copy_corpus(str(out_dir))` (line 253) copies them into the same `Corpus` directory that `FuzzerBot` reads from on the next iteration. So the bridge is "LLM writes inputs into the libFuzzer seed corpus, and the next fuzz run picks them up natively" — no special queue, no per-input message.

What the LLM actually emits is **Python source code that generates inputs**, not the inputs themselves. The compiled LangGraph (`seed-gen/src/buttercup/seed_gen/seed_task.py:19-46`) has nodes `get_context → tools → generate_seeds → execute_python_funcs → END`, where `execute_python_funcs` is `sandbox_exec_funcs(state.generated_functions, state.output_dir)`. That sandbox runs the LLM-written Python **inside wasmtime** with WASI, a 50 MB memory limit, and a single pre-opened workdir (`seed-gen/src/buttercup/seed_gen/sandbox/execute_llm_code.py:14-63`) — a meaningful defence given the LLM is about to write arbitrary `bytes` payloads.

The third workflow, `VulnBaseTask` (`seed-gen/src/buttercup/seed_gen/vuln_base_task.py:273-307`), is the *direct PoV finder*: `gather_context → tools → analyze_bug → write_pov → execute_python_funcs → test_povs`, with a self-loop back to `analyze_bug` if no valid PoV is produced (`MAX_POV_ITERATIONS = 3`, line 107). Crucially, `_test_povs` (line 166-203) runs every candidate against every FUZZER build via `ReproduceMultiple`, and successful crashes are pushed straight onto the same `CRASH` queue the fuzzer uses (line 268: `self.crash_submit.crash_queue.push(crash)`). **So the LLM is wired as a peer of the fuzzer, not just a seed-producer.**

## 5. Program Model

`ProgramModel.process_task_codequery` (`program-model/src/buttercup/program_model/program_model.py:59-95`) runs once per task and produces a `CodeQuery` database — explicitly **not** CodeQL. The implementation in `program-model/src/buttercup/program_model/codequery.py:142-178` shells out to four external binaries (`cscope`, `ctags`, `cqmakedb`, `cqsearch`) and stores a sqlite-ish file `codequery.db` alongside the source. Source extraction is "build the OSS-Fuzz container, then `docker cp container:/src host_dir`" — so the index is over **what the fuzzer container actually compiles**, not the raw repo. Tree-sitter (`program-model/src/buttercup/program_model/api/tree_sitter.py:11-12`) is layered on top for parse-tree-level queries that codequery cannot answer.

Consumers are seed-gen and patcher; both wrap the index in `CodeQueryPersistent` (`codequery.py:855-894`) which transparently rebuilds when missing and uploads the resulting `.cqdb` to shared storage. The LLM "tools" exposed in the seed-gen and patcher agents (`seed_gen/task.py:534-690`: `get_function_definition`, `get_type_definition`, `get_callers`, `cat`, plus a `batch_tool`) all bottom out in `self.codequery.get_functions / get_callers / get_types` (cqsearch subprocess calls) — i.e. the program model is exclusively an LLM-context-retrieval service, never used for static bug-finding.

## 6. Patcher

`Patcher.serve_item` (`patcher/src/buttercup/patcher/patcher.py:175-191`) pops a `ConfirmedVulnerability`, hands it to `PatcherLeaderAgent.run_patch_task()`, and on success pushes the resulting unified diff onto `QueueNames.PATCHES`. The leader (`patcher/src/buttercup/patcher/agents/leader.py:40-77`) instantiates **five sub-agents** (RootCause, SWE, QE, Reflection, ContextRetriever + an InputProcessing helper) and wires them into a `langgraph.StateGraph` with ten nodes:

```
INPUT_PROCESSING → FIND_TESTS → INITIAL_CODE_SNIPPET_REQUESTS
                 → CONTEXT_RETRIEVER → ROOT_CAUSE_ANALYSIS
                 → PATCH_STRATEGY → CREATE_PATCH → BUILD_PATCH
                 → RUN_POV → RUN_TESTS → REFLECTION
```

The enum is in `patcher/src/buttercup/patcher/agents/common.py:101-112` and a rendered PNG (`patcher/patcher_state_machine.png`) ships in-tree. `ReflectionAgent.reflect_on_patch` (`patcher/src/buttercup/patcher/agents/reflection.py:761`) classifies any failure (`PatchStatus` has nine values including `APPLY_FAILED`, `BUILD_FAILED`, `POV_FAILED`, `TESTS_FAILED`) and *routes back to the responsible node* via `ReflectionResult.decision: PatcherAgentName` (line 199-203) — so a build error re-enters `CREATE_PATCH`, but a flawed RCA re-enters `ROOT_CAUSE_ANALYSIS`. **This is what makes it a real agent loop, not a one-shot prompt.**

The patch-strategy prompt itself (`patcher/src/buttercup/patcher/agents/swe.py:128-189`) is explicit: list 2-4 alternatives, justify the pick, request more context with a `<request_information>` tag if needed, **emit strategy not code** (a separate `CREATE_PATCH` node turns strategy into a diff). Validation happens in `QEAgent.run_pov_node` (`patcher/src/buttercup/patcher/agents/qe.py:340-410`), which rebuilds the challenge with each sanitizer and re-runs every original PoV; only patches that fix *all* PoVs without breaking the test suite (`run_tests_node`, line 480) are returned via `get_successful_patch()`.

## 7. LLM orchestration via LiteLLM

Every component talks to LLMs the same way: `common/src/buttercup/common/llm.py:135-141` — `ChatOpenAI(openai_api_base=os.environ["BUTTERCUP_LITELLM_HOSTNAME"], openai_api_key=...)`. Provider switching is delegated entirely to a **LiteLLM proxy pod** whose YAML config (`litellm/litellm_config.yaml`) maps 17 logical model names (`claude-4.5-sonnet`, `openai-gpt-4.1`, `gemini-2.5-flash`, `azure-o3-mini`, …) to provider routes with per-model TPM/RPM caps. So all rate-limiting, key management, and provider failover is one config file.

Inside the apps, `create_default_llm` wraps each model in `.with_fallbacks(...)` (line 107). The seed-gen agent picks Claude 4.5 with Claude 4 → GPT-4.1 → Gemini-Pro fallbacks (`seed-gen/src/buttercup/seed_gen/task.py:96-122`); the patcher does similarly. Tracing is via Langfuse callbacks if `LANGFUSE_HOST` is reachable.

Prompts are LangChain `ChatPromptTemplate.from_messages([(system, ...), (user, ...)])` with structured XML-tagged sections (`<root_cause_analysis>`, `<code_snippets>`, `<patch_development_process>`, `<full_description>`) so downstream agents can parse them deterministically.

## 8. K8s deployment

The deployment is **plain Helm**, no operators, no CRDs. `deployment/k8s/charts/` contains a chart per bot (`build-bot`, `fuzzer-bot`, `coverage-bot`, `tracer-bot`, `merger-bot`, `patcher`, `scheduler`, `seed-gen`, `program-model`, `pov-reproducer`, `task-downloader`, `task-server`, `ui`, `scratch-cleaner`, `competition-api`, `image-preloader`, `registry-cache`, `dind-daemon`), plus vendored `litellm-helm-0.1.783.tgz`, `redis-17.17.1.tgz`, and `signoz-0.71.0.tgz`. Each app-chart template is a single `templates/deployment.yaml` rendering a `Deployment` — replica count is the only horizontal-scale knob. The one exception is `dind-daemon/templates/daemonset.yaml`, which runs Docker-in-Docker on every node so the bots can shell out to `docker build`/`docker run` for OSS-Fuzz containers without nesting.

Top-level `deployment/k8s/templates/` defines a Secret (`secrets.yaml`), ConfigMap (`config.yaml`), three `PersistentVolume`/`PersistentVolumeClaim` pairs (`persistent-volumes.yaml`), and a Job (`litellm-user-keys-job.yaml`) that pre-provisions per-component LiteLLM API keys with their own RBAC. **No custom resources.**

## 9. Hot reproducer pattern

AIxCC required every finding to be reproducible from a single input. Buttercup makes the input itself a **first-class field on every message that flows downstream from a crash**: `Crash.crash_input_path` (proto line 90), copied into `TracedCrash` and again into each `CrashWithId` inside the persistent `SubmissionEntry`. The path always points to shared storage and `node_local.make_locally_available()` (e.g. `patcher/.../patcher.py:112`, `pov_reproducer.py:70`) pulls the gzip on demand wherever the worker happens to land.

The dedicated **POVReproducer** bot (`orchestrator/src/buttercup/orchestrator/pov_reproducer/pov_reproducer.py`) is the gate between "we have a patch" and "we ship it to competition." It consumes `POVReproduceRequest` messages that the `Submissions` state machine inserts (`submissions.py:1570-1601`, one per PoV × per patch-build × per-sanitizer), fetches the matching `BuildType.PATCH` build from the `BuildMap` (line 56-62), runs `ChallengeTask.reproduce_pov(harness, local_path)` (`common/challenge_task.py:704-749`, which is OSS-Fuzz's `helper.py reproduce` with a 120 s timeout and propagated exit code), and marks the entry `mitigated` / `non_mitigated` in a Redis set (`PoVReproduceStatus`). Only when `_check_all_povs_are_mitigated()` returns `True` does `_submit_patch_if_good` push the patch to the competition API. The same exit-code reproduction is also what `QEAgent.run_pov_node` uses inside the patcher LangGraph (`qe.py:375`) — so the *very same* reproducer logic is invoked once inside the patcher (fast iteration) and again outside it (final gating).

## 10. What's genuinely novel at the code level

(1) **LLM as a fuzzer peer, not a fuzzer assistant.** `VulnBaseTask` pushes its successfully-crashing LLM-generated inputs onto the exact same `QueueNames.CRASH` stream the `FuzzerBot` writes to (`vuln_base_task.py:268`) — the rest of the pipeline (tracer, deduper, scheduler, patcher) cannot tell whether a finding came from libFuzzer or from a Claude prompt. (2) **wasmtime-sandboxed LLM Python execution** (`sandbox/execute_llm_code.py:34-63`) for the seed-generator, which is a more aggressive isolation choice than the more common "run it in a subprocess with `seccomp`" pattern and is the kind of thing only a security-focused team builds. (3) **A single `process_cycle()` linearised state machine** for every PoV-patch-bundle lifecycle (`submissions.py:1751`), persisted to Redis on every transition inside a `pipeline()` so it is fully restart-safe — replacing what most CRS designs implement as a Celery/Airflow DAG with ~1800 lines of explicit Python and a protobuf `SubmissionEntry`.
