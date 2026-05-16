# RESTler — code-level analysis

RESTler is a stateful black-box REST API fuzzer. It is unusual among fuzzers in being a two-language pipeline: an F#/.NET *Compiler* statically analyzes an OpenAPI/Swagger spec and emits a self-contained Python *grammar*, which a separate Python *Engine* then executes against the target service while applying a battery of *Checkers*. There is no shared in-process state between the two halves — the contract is the on-disk `grammar.py` plus `dict.json` + `engine_settings.json` (`src/compiler/Restler.Compiler/Workflow.fs:16-26`).

## 1. Architecture overview

Three stages run in sequence; the entry orchestrator is `restler/restler.py` and `src/compiler/Restler.Compiler/Workflow.fs`:

1. **Compiler** (F#): `generateRestlerGrammar` in `src/compiler/Restler.Compiler/Workflow.fs:234` reads the spec via NSwag, runs producer-consumer dependency inference, then calls `CodeGenerator.Python.generateCode` (`Workflow.fs:31`) to emit `grammar.py`.
2. **Engine** (Python): `restler.py:589` spawns a `FuzzingThread` that drives `engine.core.driver.generate_sequences` (`restler/engine/core/driver.py:644`). It iteratively extends sequences and renders them against the target.
3. **Checkers** (Python): every rendered sequence is handed to each enabled checker via `CheckerBase.apply` (`restler/checkers/checker_base.py:60`), which mutates or replays the sequence to detect a specific class of semantic bug. A background `GarbageCollectorThread` (`restler/engine/dependencies.py:590`) DELETEs created resources concurrently.

## 2. Module / package layout

F#/.NET, all under `src/compiler/Restler.Compiler/` (~9.6 kloc):

- `Swagger.fs` + `SwaggerSpecPreprocessor.fs` + `SwaggerVisitors.fs` — spec loading via NSwag and JSON-pointer schema visiting.
- `Grammar.fs` — the *internal* grammar AST (`OperationMethod`, `ParameterKind`, `PrimitiveType`, `RequestPrimitiveType` are all algebraic data types — `src/compiler/Restler.Compiler/Grammar.fs:76-130`).
- `Compiler.fs` — the orchestrator; `generateRequestGrammar` at `Compiler.fs:1160` ties everything together.
- `Dependencies.fs` (2086 lines, the largest single file) — producer/consumer inference.
- `DependencyAnalysisTypes.fs` — the indexed `Producers` container backing the inference.
- `Annotations.fs` — user-supplied producer/consumer overrides.
- `Dictionary.fs` — fuzzing value dictionary.
- `CodeGenerator.fs` — emits Python via `generateCode` (`CodeGenerator.fs:1289`).

Python, under `restler/` (~14 kloc in engine + checkers):

- `restler/engine/core/` — `driver.py` (main loop), `sequences.py` (sequence + render), `requests.py` (1965-line request model), `fuzzing_monitor.py`, `request_utilities.py`, `preprocessing.py`.
- `restler/engine/fuzzing_parameters/` — schema/value combinatorics (`body_schema.py`, `param_combinations.py`, `parameter_schema.py`, `request_params.py`).
- `restler/engine/dependencies.py` — dynamic-variable TLB and the garbage collector.
- `restler/engine/primitives.py` — the runtime types referenced by the generated grammar (`restler_static_string`, `restler_fuzzable_*`, etc.; constants at `restler/engine/primitives.py:34-52`).
- `restler/checkers/` — one file per checker.

## 3. Compiler (Swagger → Python grammar)

Pipeline driven by `Workflow.fs:76 generateGrammarFromSwagger`:

1. `Swagger.getSwaggerDocument` (`SwaggerVisitors.fs`) loads each spec via NSwag's `OpenApiDocument`.
2. For each `(endpoint, method)` pair, `getRequestData` in `Compiler.fs:1166` builds a `RequestParameters` record with path / query / header / body slots, each populated by `Parameters.getAllParameters` / `Parameters.pathParameters` / `Parameters.getBody` (`Compiler.fs:1237-1278`). Body schemas are walked recursively by `SwaggerVisitors.fs` to produce a `Tree<LeafProperty,InnerProperty>` (the generic tree from `Grammar.fs:13`).
3. `Restler.Dependencies.extractDependencies` is invoked at `Compiler.fs:1421` to assign a *producer* to every *consumer* parameter — see §4.
4. `getResponseParsers` (`Compiler.fs:83`) walks the resulting dependency list and, per request, builds a `RequestDependencyData` that lists which response JSON paths to extract (the *writer variables*) and which dynamic objects to inject (the *reader variables*).
5. `generateRequestPrimitives` (`Compiler.fs:764`, invoked at `Compiler.fs:1471`) flattens each request to an ordered list of `RequestPrimitiveType` cases (`CodeGenerator.fs:35-58`):
   ```
   Restler_static_string_constant | Restler_fuzzable_string | Restler_fuzzable_uuid4
   | Restler_custom_payload | Restler_custom_payload_uuid4_suffix
   | Response_parser | ...
   ```
6. `CodeGenerator.Python.generateCode` (`CodeGenerator.fs:1289`) renders that list as one Python `request_collection` literal containing tuples of these primitive names — names that match the Python runtime constants in `restler/engine/primitives.py:34-52`. The 1-to-1 type mapping is the cross-language contract; the comment "All primitives must be supported in restler/engine/primitives.py" lives at `CodeGenerator.fs:34`.

The compiler also writes `dict.json`, `dependencies.json`, `engine_settings.json`, and a `custom_value_gen_template.py` (`Workflow.fs:182-200`).

## 4. Producer-consumer dependency inference

This is the algorithm that lets RESTler synthesize `POST /widgets` → `GET /widgets/{id}` chains without any user hints. It runs in `Restler.Dependencies` (`src/compiler/Restler.Compiler/Dependencies.fs`).

**Data structures** (`DependencyAnalysisTypes.fs:62-175`): a `Producers` object holds, per-resource-name, four parallel indexes:
- `sortedByMatch` / `sortedByMatchNonNested` — a `SortedList` keyed by `(methodRank, endpointPattern, accessPathLength, tiebreaker)` defined in `inferredMatchSort` (`DependencyAnalysisTypes.fs:38-53`). The sort biases POST > PUT > PATCH > GET (`sortByMethod`, line 27) — i.e. a fresh resource creator is always preferred over a reader.
- `indexedByEndpoint : Dictionary<RequestId, List<ResponseProducer>>`.
- `indexedByTypeName : Dictionary<string, List<ResponseProducer>>` (multi-key index across all `CandidateTypeNames` for fuzzy matching).
- `samePayloadProducers` and `inputOnlyProducers` for the unusual case of values introduced in the request body that later need to be referenced.

**Algorithm** (`Dependencies.fs:1136 extractDependencies`):

1. Walk every request and harvest *consumers* in parallel via `Array.Parallel.map` over path / query / header / body parameter lists (`Dependencies.fs:1166-1255`).
2. Walk every response schema and register *producers* into the `Producers` index above (POST / PUT / GET are eligible; `AddResponseProducer` at `DependencyAnalysisTypes.fs:91`).
3. For each consumer, call `findProducer` (`Dependencies.fs:688`), which delegates to `findProducerWithResourceName` (`Dependencies.fs:287`). Three heuristics, tried in order:
   - **Explicit annotation match** (`Dependencies.fs:358-415`) — user-supplied `producer_endpoint` / `producer_resource_name` from `annotations.json` overrides everything.
   - **Path-prefix match** for path parameters: if the consumer endpoint is `/api/foo/{fooId}/bars/{barId}`, look for a PUT/POST/GET on the prefix `/api/foo/{fooId}/bars` whose response carries `fooId` (`Dependencies.fs:310-356`). Validity is checked by `isValidProducer` (`Dependencies.fs:23-52`), which enforces the rule that a POST producer can satisfy any consumer method, a PUT producer can satisfy anything except POST, etc.
   - **Same-name / type-name match in nested body objects** via `getNestedObjectProducer` (`Dependencies.fs:219-281`), using the per-property `CandidateTypeNames` (camel-case decomposition).
4. A special-case `getCreateOrUpdateProducer` (`Dependencies.fs:89-152`) handles the PUT-creates-via-id pattern by injecting a `restler_custom_payload_uuid4_suffix` dictionary entry so PUT requests can self-produce a fresh ID.
5. A second pass `mergeDynamicObjects` (`Compiler.fs:1442`) fixes cases where the per-request scan missed an input-producer because the same parameter was already classified as a reader.

The result is a `Dictionary<string, List<ProducerConsumerDependency>>` plus an ordering-constraint list, both serialized to `dependencies.json` and `dependencies_debug.json` (`Workflow.fs:202-211`).

At engine runtime the linkage is materialized through string placeholder substitution. Every producer-writer emits `dependencies.DynamicVariable("...")` definitions and every consumer-reader splats a `_READER_DELIM<type>_READER_DELIM` placeholder into the request body (`restler/engine/dependencies.py:41,55-82`). `Request._set_constraints` (`restler/engine/core/requests.py:351`) scans the rendered definition for those delimiters to populate `self._consumes` / `self._produces`. This is what makes the entire dependency graph traverable in Python without any AST — it's just substring grep.

## 5. Engine sequence generation

`generate_sequences` in `restler/engine/core/driver.py:644` is the core loop. It starts with `seq_collection = [Sequence()]` (the empty sequence, `driver.py:685`) and, at each *generation* `g = 1..max_sequence_length`, calls:

```python
seq_collection, extended_requests = extend(seq_collection, fuzzing_requests, ...)   # driver.py:813
seq_collection = render(seq_collection, ...)                                         # driver.py:836
```

`extend` (`driver.py:62-130`) takes every request `req` from the fuzzing pool, every existing sequence `seq`, and appends `req` to `seq` **iff** `validate_dependencies(req, seq)` succeeds — i.e. every dynamic variable in `req.consumes` is in the union of `produces` of the requests already in `seq` (`driver.py:42-59`). Scheduling depends on `Settings().fuzzing_mode`:

- `'bfs'` / `'test-all-combinations'` — exhaustive: append to every compatible sequence (`driver.py:95-114`).
- `'bfs-fast'` / `'bfs-minimal'` — each request appended to exactly one sequence (`driver.py:116-118`).
- `'random-walk'` — after extension, truncate `seq_collection` to one randomly-chosen sequence (`driver.py:125-128`); the outer `while not should_stop` loop is only kept alive in this mode (`driver.py:699-700`).
- `'directed-smoke-test'` — pre-computes the minimum sequence per request via `compute_request_goal_seq` (`driver.py:721-727`).

`render_sequential` / `render_parallel` (`restler/engine/core/sequences.py:299-345`) hand each sequence to `Sequence.render` (`sequences.py:420`). Inside, `render_prefix` (`sequences.py:449`) replays all but the last request using the *last-known-valid* combination ID, while the last request iterates through all value combinations until one returns a 2xx. Only valid renderings are kept and become building blocks for the next generation — this is RESTler's "stateful corpus": grow only from sequences that the server actually accepted (`sequences.py:255-291`).

Two perf knobs: the `RenderedSequenceCache` (`driver.py:791` and `render_with_cache` at `sequences.py:347`) caches prefix renderings keyed by the prefix request list; `create_prefix_once` (`sequences.py:457-464`) avoids re-rendering an expensive prefix on every combination.

## 6. Fuzzing strategies

Two value sources feed every fuzzable primitive:

- **Mutation dictionary** (`dict.json`, parsed in F# by `Dictionary.fs`, consumed in Python by `engine.primitives.CandidateValuesPool`). Per-type lists of `restler_fuzzable_string`, `_int`, `_bool`, `_datetime`, plus `restler_custom_payload[_header|_query|_uuid4_suffix]` (`restler/engine/primitives.py:34-52`).
- **Value generators** — Python callables loaded from `custom_value_gen_template.py`; `is_value_generator` checks the wrapper name (`restler/engine/primitives.py:75-80`).

**Body schema fuzzing** is structural rather than per-value and lives in `restler/engine/fuzzing_parameters/`:

- `BodySchema` (`fuzzing_parameters/body_schema.py:26`) wraps a `ParamObject` tree built from the compiler-emitted JSON schema.
- `BodySchemaStructuralFuzzer.run` (`restler/checkers/body_schema_fuzzer.py:37`) takes a seed schema, calls `schema_seed.get_fuzzing_pool(self, config)`, and returns up to `max_combination` schema variants. The mutators (drop required, duplicate, type-confuse, depth-blowup) are implemented in `JsonBodySchemaFuzzerBase` (`engine/fuzzing_parameters/param_combinations.py`).
- Header/query parameter combinatorics live in `engine/fuzzing_parameters/param_combinations.py:16-80` (`get_param_list_combinations`, `filter_required`, `choose_n`).

"Smart" vs random is mostly a knob on `max_combinations` plus `propagate_strategy` ('EX' = Cartesian, others = sampled) at `checkers/body_schema_fuzzer.py:84-96`.

## 7. Checkers

All registered in `restler/checkers/__init__.py:7-14`; each subclasses `CheckerBase` (`restler/checkers/checker_base.py:25`) and implements `apply(rendered_sequence, lock)`. Highlights:

- **LeakageRuleChecker** (`leakage_rule_checker.py:17`) — fires only when a rendering *failed* (`apply:36`). If the failed request was supposed to create a resource, the checker tries to fetch the resource it claimed to make; a 2xx means the server leaked a partially-created object.
- **ResourceHierarchyChecker** (`resource_hierarchy_checker.py:14`) — swaps a child's parent for an unrelated parent's ID to see if cross-tenant access is permitted.
- **UseAfterFreeChecker** (`use_after_free_checker.py:19`) — only runs when the last request in the sequence is a destructor (`apply:45`). It then locates every other request that consumes the same types (`use_after_free_checker.py:78-90`) and tries them after the DELETE; a 2xx is a UAF bug.
- **NameSpaceRuleChecker** (`namespace_rule_checker.py:20`) — only runs when two auth tokens are configured (`apply:56-59`); re-issues a request authored by user A with user B's token to detect cross-tenant access.
- **InvalidDynamicObjectChecker** (`invalid_dynamic_object_checker.py:16`) — replaces a freshly-minted dynamic object with garbage and resends; checks for missing input validation.
- **PayloadBodyChecker** (`payload_body_checker.py:36`, 1298 lines) — the heaviest checker; uses `BodySchemaStructuralFuzzer` plus a `ResponseTracker` and `PayloadBodyBuckets` (`payload_body_bucketing.py`) to dedupe semantically-similar response shapes.
- **InvalidValueChecker** (`invalid_value_checker.py:1`) — replays each fuzzable primitive with values from `invalid_value_checker_value_gen.py` plus optional user generators.
- **ExamplesChecker** (`examples_checker.py`) — re-runs requests with the exact payloads from the OpenAPI `examples` section.

Example of how a checker chains onto an existing sequence — the entire UAF logic in one block (`use_after_free_checker.py:78-98`):

```python
for request in self._fuzzing_requests:
    if request.hex_definition == destructor.hex_definition: continue
    if request.consumes == destructed_types:
        consumers.append(copy.copy(request))
for request in consumers:
    self._render_last_request(self._sequence + sequences.Sequence(request))
    if self._mode != 'exhaustive': break
```

All checkers share `_render_and_send_data` (`checker_base.py:101`), which renders the request via the same primitives pipeline but uses its own thread-local socket so checker traffic does not interfere with the main fuzzer's connection state (`checker_base.py:86-90`).

## 8. Garbage collector

Created in `restler.py:578-586` only when `--garbage_collection_interval` or `run_gc_after_every_sequence` is set. Two classes in `restler/engine/dependencies.py`:

- `GarbageCollector` (`dependencies.py:259`) — owns `dyn_objects_cache`, `saved_dyn_objects`, `overflowing`, `async_deletions`, `gc_stats` dicts.
- `GarbageCollectorThread` (`dependencies.py:590`) — a daemon thread that wakes on `cleanup_event` or after the interval and calls `GarbageCollector.run` (`dependencies.py:328`).

`do_garbage_collection` (`dependencies.py:375`):
1. Locks `dyn_objects_cache`, then per dynamic object type scans `self.req_collection` for a request flagged `is_destructor()` whose `consumes` is the singleton `{object_type}` (`dependencies.py:395-408`). Preference is given to a destructor whose endpoint *ends with* a path parameter of that exact type ("found destructor where the final variable in the endpoint is the correct type", line 406) — a syntactic heuristic to avoid DELETing a parent and orphaning siblings.
2. Moves anything beyond `dyn_objects_cache_size` from the live cache into `overflowing`, **releases the lock**, then issues actual DELETEs in `apply_destructors` (`dependencies.py:434`). The release-before-delete pattern is documented at `dependencies.py:378-383` and is important: HTTP DELETEs can take seconds and must not block the fuzzer registering new dynamic objects.
3. Async deletes (202-style) are polled via `try_async_poll` and tracked in `self.async_deletions[type]` (`dependencies.py:485+`).

A `finish()` step (`dependencies.py:350`) merges the protected `saved_dyn_objects` set back into the cache so post-fuzzing teardown wipes everything.

## 9. What's genuinely novel at the code level

The Swagger-to-stateful-grammar pipeline is the actual research contribution: a two-language separation where the compiler can do heavyweight inference offline in a strongly-typed setting (the algebraic data types in `Grammar.fs:35-58` and the multi-index `Producers` cache in `DependencyAnalysisTypes.fs:62-70` would be painful to express in Python), while the engine becomes a thin stateful executor whose contract is just primitive names matching `restler/engine/primitives.py:34-52`. The dependency inference itself (`Dependencies.fs:23-52, 287-415, 1136-1442`) is essentially a static-analysis pass on a REST spec — naming-convention heuristics, validity rules per HTTP method, and a sorted producer index — and it is what makes RESTler synthesize multi-request chains without recordings. Finally, the substring-based dynamic-variable plumbing (`_READER_DELIM` markers parsed by `_set_constraints` at `restler/engine/core/requests.py:351`) lets every checker compose new sequences just by concatenating `Sequence` objects without re-parsing or rebuilding state — the basis for how UAF, leakage, hierarchy and namespace checkers can each express their attack in 20-50 lines.
