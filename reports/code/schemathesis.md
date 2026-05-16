# Schemathesis — code-level analysis

## 1. Architecture overview

Schemathesis presents three entry surfaces that share the same generation/runner core:

- **CLI** — `schemathesis` Click group at `src/schemathesis/cli/commands/__init__.py:45`, with `run` (`src/schemathesis/cli/commands/run/__init__.py:1`) and `fuzz` subcommands wired in at `src/schemathesis/cli/commands/__init__.py:140`.
- **Python loader API** — `schemathesis.openapi.from_path` / `from_url` / `from_asgi` / `from_wsgi` at `src/schemathesis/openapi/loaders.py:133,90,28` and a matching GraphQL trio at `src/schemathesis/graphql/loaders.py:127,89,27`. All converge on `from_dict`, producing an `OpenApiSchema` / `GraphQLSchema`.
- **pytest plugin** — registered as a pytest entry point and implemented in `src/schemathesis/pytest/plugin.py:333` (`pytest_pycollect_makeitem`), `:485` (`pytest_configure`). The decorator `@schema.parametrize()` stamps a function with `SchemaHandleMark` (`:83`) that the collector hook then sees.

The shared pipeline is: **load schema → APIOperation iteration → `operation.as_strategy(...)` returns a `hypothesis.SearchStrategy[Case]` → engine draws a `Case`, sends via a transport, then runs check predicates**. The composite strategy entry point for OpenAPI is `openapi_cases` at `src/schemathesis/specs/openapi/_hypothesis.py:93`; the corresponding test wrapper is built in `create_test` at `src/schemathesis/generation/hypothesis/builder.py:98`, where one Hypothesis test is assembled as `st.one_of(operation.as_strategy(generation_mode=mode, …) for mode in generation.modes)` (`builder.py:114`).

## 2. Module / package layout

Under `src/schemathesis/`:

- `cli/` — Click application. `commands/__init__.py` declares the root group; `commands/run/` has the test-runner subcommand; `commands/fuzz/` the continuous fuzzer. Report writers live in `cli/commands/run/handlers/` (allure, har, junitxml, ndjson, vcr).
- `generation/` — schema-agnostic generation layer. `generation/hypothesis/builder.py` wires Hypothesis settings, phases, and seeds to a strategy; `generation/case.py` is the `Case` dataclass; `generation/meta.py` holds `CoverageScenario` and `PhaseInfo`; `generation/stateful/state_machine.py` is the schema-agnostic `APIStateMachine` base class.
- `checks.py` — registry, decorator, and runner for response-validation predicates.
- `engine/` — the runner. `engine/control.py` (failure / time budget), `engine/run/unit/_layered_scheduler.py` (dependency-layered work queue), `engine/run/stateful/` (stateful test wiring), `engine/recorder.py` (per-scenario interaction log), `engine/statistic.py` (failure dedup, coverage of operations).
- `specs/openapi/` — the heavyweight OpenAPI module: `_hypothesis.py` (composite case strategy), `checks.py` (~1184 lines of API-aware checks), `coverage/_schema.py` (~2539 lines of constraint enumeration), `coverage/_operation.py` (combinator producing concrete cases), `negative/` (schema-mutating "negative" generator), `stateful/links.py` and `stateful/inference.py` (OpenAPI Links + heuristic link inference from `Location` headers).
- `specs/graphql/` — GraphQL parallel: `stateful/_rules.py` (producer/consumer bundles), `inference.py` (operation classification), `scalars.py`, `substitution.py`.
- `transport/` — pluggable sender: `transport/requests.py`, `transport/wsgi.py`, `transport/asgi.py`; `prepare.py` builds the kwargs.
- `hooks.py` — hook dispatcher and decorators for user customization.
- `pytest/` — pytest plugin (`plugin.py`), lazy schema loader (`lazy.py`, `loaders.py`), xdist support.
- `config/` and `core/` — TOML config, registries, `Failure` hierarchy, JSON Schema helpers.

There is no top-level `_hypothesis/` directory; the OpenAPI strategy lives in `specs/openapi/_hypothesis.py` and the Hypothesis test glue lives in `generation/hypothesis/`.

## 3. Hypothesis integration

This is the central subsystem. `openapi_cases` (`specs/openapi/_hypothesis.py:93`) is the `@st.composite` strategy that draws one `Case`. It calls `generate_parameter(location, …)` for each of `PATH`, `HEADER`, `COOKIE`, `QUERY` (`_hypothesis.py:132,145,158,171`), then picks a body candidate and a concrete media type (`_hypothesis.py:185-231`), then assembles a `Case` with full `CaseMetadata` (`_hypothesis.py:382-408`). Positive generation delegates to `hypothesis-jsonschema`:

```python
# src/schemathesis/specs/openapi/_hypothesis.py:853
def make_positive_strategy(schema, …):
    custom_formats = _build_custom_formats(generation_config, GenerationMode.POSITIVE)
    return from_schema(schema, custom_formats=custom_formats, …)
```

Mode selection is done in `GENERATOR_MODE_TO_STRATEGY_FACTORY` (`_hypothesis.py:907`):

```python
GENERATOR_MODE_TO_STRATEGY_FACTORY = {
    GenerationMode.POSITIVE: make_positive_strategy,
    GenerationMode.NEGATIVE: make_negative_strategy,
}
```

**Per-type translation, three examples:**

- **`string` with `format: email`** — a strategy is registered in `get_default_format_strategies()` at `src/schemathesis/specs/openapi/formats.py:138`: `"email": st.emails().map(_lowercase_email_domain)` (line 158). The lowercasing is a deliberate workaround for `hypothesis.strategies.emails()` producing mixed-case `Xn--` IDN ACE prefixes that `jsonschema_rs` then rejects per RFC 3490 (comment at `formats.py:152-154`). The dict is fed to `from_schema(..., custom_formats=custom_formats)`.
- **`integer` with `minimum`/`maximum`** — handed straight to `hypothesis_jsonschema.from_schema`; for coverage mode the boundary scenarios `MINIMUM_VALUE`, `MAXIMUM_VALUE`, `NEAR_BOUNDARY_NUMBER`, `VALUE_BELOW_MINIMUM`, `VALUE_ABOVE_MAXIMUM` are enumerated explicitly in `specs/openapi/coverage/_schema.py` (`CoverageScenario` enum at `src/schemathesis/generation/meta.py:42-44,61-62`); `_shift_by_multiple` (`coverage/_schema.py:1720`) computes the just-below / just-above adjacent integers when `multipleOf` is present.
- **`array` with `items`** — recursive call into the schema walker via `cover_schema_iter` (`coverage/_schema.py:954`). For positive mode it emits `VALID_ARRAY`, `MINIMUM_ITEMS_ARRAY`, `MAXIMUM_ITEMS_ARRAY`, `ENUM_VALUE_ITEMS_ARRAY` (`generation/meta.py:46-50`); for negative mode `ARRAY_ABOVE_MAX_ITEMS`, `ARRAY_BELOW_MIN_ITEMS`, `NON_UNIQUE_ITEMS` (`meta.py:69-70,85`).

**Negative generation** is its own pipeline at `src/schemathesis/specs/openapi/negative/__init__.py:223` (`negative_schema`). It splits the schema into `keywords` + `non_keywords` (`split_schema` at `:196`), builds a `jsonschema_rs.Validator` from the original schema, and runs schema-level mutations (operators in `negative/mutations.py`). The output strategy is `from_schema(mutated_schema, ...).filter(filter_values).map(lambda v: GeneratedValue(v, metadata))` (lines 277-285). A "value channel" fires with probability 0.15 (`VALUE_CHANNEL_PROBABILITY`, `:35`) that takes a *valid* body and surgically violates one keyword in-place (`hybrid` composite, lines 324-355). For JSON bodies, ~5% of cases (`SYNTAX_FUZZING_PROBABILITY`, `:34`) are replaced with raw non-JSON bytes via `_random_non_json_bytes()` (`:50`) — a syntax-level rather than semantic mutation.

## 4. Built-in checks

Checks are registered through a single decorator on a global `Registry`:

```python
# src/schemathesis/checks.py:108,116
CHECKS = Registry[CheckFunction]()

def check(func: CheckFunction) -> CheckFunction:
    return CHECKS.register(func)
```

The spec-agnostic `not_a_server_error` (`src/schemathesis/checks.py:138`) and `max_response_time` (`checks.py:185`) live there. Spec-specific ones are in `src/schemathesis/specs/openapi/checks.py`, all gated by `@requires_openapi_schema` / `@skips_on_unexpected_http_status` (`checks.py:60,74`):

- `status_code_conformance` — `specs/openapi/checks.py:105`, raises `UndefinedStatusCode` when the response code is outside the documented set (handling `"default"` and `2XX` wildcards via `expand_status_codes`).
- `content_type_conformance` — `:132`, parses `Content-Type` with `media_types.parse` and matches against documented options, raising `MissingContentType` / `UndefinedContentType` / `MalformedMediaType`.
- `response_headers_conformance` — `:177`, walks the response definition's headers and runs each header value through the per-header `jsonschema_rs.Validator`.
- `response_schema_conformance` — `:263`, dispatches to `case.operation.validate_response(response, case=case)`.
- `negative_data_rejection` — `:570`, in negative mode requires a 4xx (configurable allowed set); raises `AcceptedNegativeData`. Has six "becomes-valid-after-serialization" guards (`_body_negation_becomes_valid_after_serialization`, `_single_element_array_becomes_valid_after_serialization`, etc., lines 277-563) that suppress false positives where a mutation is silently neutralised by transport encoding.
- `positive_data_acceptance` — `:668`, the dual: in positive mode the server must return a documented success code, otherwise emits `RejectedPositiveData` with an `additionalProperties` hint (`_additional_properties_hint`, `:624`).
- `use_after_free` — `:862`, traverses related cases via `ctx._find_related`, finds a prior DELETE on a path that prefixes the current case (`_is_prefix_operation`), and confirms the resource wasn't recreated (`_resource_recreated_after_delete`) before raising `UseAfterFree`.
- `ensure_resource_availability` — `:921`, the symmetric "resource visible to its creator" check on 404 responses.
- `ignored_auth` — `:997`, when a secured operation returns 2xx, the check actively re-sends the case with auth stripped and with a fabricated bad credential (`remove_auth`, `set_auth_for_case` at `specs/openapi/_auth_retry.py`); a non-401 response raises `IgnoredAuth`.

Sample implementation, abbreviated:

```python
# src/schemathesis/specs/openapi/checks.py:105
@schemathesis.check
@requires_openapi_schema
@skips_on_unexpected_http_status
def status_code_conformance(ctx, response, case):
    status_codes = case.operation.responses.status_codes
    if "default" in status_codes: return None
    allowed = list(_expand_status_codes(status_codes))
    if response.status_code not in allowed:
        raise UndefinedStatusCode(...)
```

## 5. Stateful runner

`APIStateMachine` at `src/schemathesis/generation/stateful/state_machine.py:156` subclasses Hypothesis's `RuleBasedStateMachine`. Per-step inputs/outputs are `StepInput` / `StepOutput` dataclasses (`:46,142`); transition metadata is in `Transition` (`:71`) with `ExtractedParam` (`:85`) wrapping `Result[Any, Exception]` so a failed expression extraction is first-class data. Default settings disable Hypothesis's deadline and set `stateful_step_count=DEFAULT_MAX_SCENARIO_STEPS` (`:34-39`).

The `step()` method (`:300`) calls `before_call` → `get_call_kwargs` → `call` → `after_call` → `validate_response`, where `validate_response` (`:341`) chains into `Case.validate_response`, running the registered checks for each step.

For OpenAPI, sequences are derived from two sources:

1. **OpenAPI Links (spec-driven)** — `src/schemathesis/specs/openapi/stateful/links.py:32` defines `OpenApiLink`; parameters are resolved through OpenAPI runtime expressions in `specs/openapi/expressions/`. Each link becomes a Hypothesis `rule` that consumes from the source-operation bundle.
2. **Inferred Links (heuristic)** — `src/schemathesis/specs/openapi/stateful/inference.py:78` (`LinkInferencer.from_schema`) builds a Werkzeug routing `Map` from all operation paths, then on every response looks at the `Location` header, finds exact + prefix operations, and synthesises a link with `{"is_inferred": True}` (`OperationById.to_link_base`, `:43`). This means CRUD shapes that omit OpenAPI `links` still get exercised statefully — Schemathesis routes 201 responses' `Location` headers back into matching GET/PUT/DELETE operations.

GraphQL takes a fundamentally different route in `src/schemathesis/specs/graphql/stateful/_rules.py:62`: every nullable / non-null `ID`-typed return value becomes a `Bundle`, every operation whose argument type matches a bundle becomes a `consumer` rule via `consumes(...)`, and `iter_operation_summaries` (`:62`) classifies each field as `PRODUCER` / `CONSUMER` / `CLEANUP` based on naming heuristics (`CLEANUP_PREFIXES`). Cleanup rules push consumed ids into a `deleted_<TypeName>_ids` bundle and `BASE_EXPLORATION_RATE = 0.15` (`state_machine.py:43`) controls how often a fresh (likely-unknown) id is drawn instead of one from the alive bundle, deliberately probing use-after-delete behaviour.

Max-failures handling is in `ExecutionControl` (`src/schemathesis/engine/control.py:14`):

```python
# src/schemathesis/engine/control.py:67
def count_failure(self):
    if self.max_failures is not None:
        self._failures_counter += 1
        if self._failures_counter >= self.max_failures:
            self.has_reached_the_failure_limit = True
```

`is_stopped` (`:55`) is then `is_interrupted or has_reached_the_failure_limit or has_reached_time_limit`, polled by the runner loop; `StopReason` (`:74`) records which budget triggered.

## 6. CLI

Built on **Click**. The root group is `schemathesis = click.group(...)` at `src/schemathesis/cli/commands/__init__.py:45`. Subcommands attached on lines 140-150 (`run`, `fuzz`); `run`'s function is decorated with ~40 `grouped_option`s in `cli/commands/run/__init__.py:83-160`. The custom `CommandWithGroupedOptions` / `StyledGroup` classes (in `cli/ext/groups.py`) bucket options into named sections for `--help`.

Report writers are pluggable `EventHandler`s registered when CLI flags fire:

- `cli/commands/run/handlers/junitxml.py:16` — `JunitXMLHandler` (`record_scenario` per `ScenarioFinished`)
- `cli/commands/run/handlers/ndjson.py` — line-delimited JSON
- `cli/commands/run/handlers/vcr.py` — VCR cassettes
- `cli/commands/run/handlers/har.py` — HAR file
- `cli/commands/run/handlers/allure.py` — Allure
- `cli/commands/run/handlers/output.py` — the human terminal renderer

There are **no `replay` or `auth` subcommands** in this checkout — `commands/` contains only `data.py`, `run/`, and `fuzz/`. Auth retry logic is internal to the `ignored_auth` check (`specs/openapi/_auth_retry.py`), not exposed as a CLI verb.

## 7. Pytest plugin

The plugin in `src/schemathesis/pytest/plugin.py` registers via the `pytest11` entry point. The user writes:

```python
schema = schemathesis.openapi.from_path("openapi.yaml")
@schema.parametrize()
def test_api(case): ...
```

`@schema.parametrize()` tags the function with `SchemaHandleMark` (`plugin.py:83`). At collection time, `pytest_pycollect_makeitem` (`:333`) inspects the marker:

```python
# src/schemathesis/pytest/plugin.py:333
@hookimpl(hookwrapper=True)
def pytest_pycollect_makeitem(collector, name, obj):
    outcome = yield
    schema = SchemaHandleMark.get(obj)
    outcome.force_result(SchemathesisCase.from_parent(collector, test_function=obj, name=name, schema=schema))
```

`SchemathesisCase` (`:104`, a `PyCollector` subclass) replaces normal pytest item collection. Its `_gen_items` (`:134`) iterates the schema's API operations, invokes `create_test` (`generation/hypothesis/builder.py:98`) per operation to wrap the user function with `@hypothesis.given(strategy)`, then yields one `SchemathesisFunction` (a `pytest.Function` subclass, `:87`) per operation labelled `"test_api[GET /pets]"` (`_get_test_name`, `:131`).

`pytest_exception_interact` (`:370`) trims Schemathesis-internal traceback frames and deduplicates identical exceptions inside `BaseExceptionGroup`; `pytest_pyfunc_call` (`:413`) intercepts `FailedHealthCheck` / `Unsatisfiable` / `InvalidArgument` from Hypothesis and renders them through the schemathesis-style error formatters in `generation/hypothesis/reporting.py`. A lazy variant in `pytest/lazy.py` defers schema loading until pytest fixtures resolve, so a `from_fixture("api_schema")` pattern works.

## 8. Coverage measurement

There are two senses of "coverage" in the code:

1. **Operations-exercised bookkeeping** — `engine/statistic.py:33`, the `Statistic` dataclass. `tested_operations: set[str]` is populated inside `on_scenario_finished` (`:91-98`):

```python
# src/schemathesis/engine/statistic.py:91
for case_id, case in recorder.cases.items():
    checks = recorder.checks.get(case_id, [])
    if not checks:
        self.cases_without_checks += 1
        continue
    self.tested_operations.add(case.value.operation.label)
```

So "operations hit" is exactly the set of `operation.label` strings (`"GET /users/{id}"`) for which at least one check ran. `total_cases`, `cases_with_failures`, `cases_without_checks` track aggregate volume. `unique_failures_map: dict[Failure, str]` (`:38`) deduplicates by the `Failure` value's `__hash__`, so each distinct violation is reported once even across thousands of cases.

2. **Constraint-coverage scenarios** — orthogonal to operation coverage. The `coverage` phase enumerates `CoverageScenario` values (`generation/meta.py:21`) per operation: 16 positive scenarios (boundary lengths, enum, default, only-required, etc.) and ~15 negative scenarios (type/format/pattern violations, missing required, duplicate parameter, unspecified HTTP method). Each generated case carries `CoveragePhaseData(scenario=...)` in `case.meta.phase.data`, which check decorators consult — e.g. `is_unexpected_http_status_case` (`specs/openapi/checks.py:51`) suppresses conformance checks for `UNSPECIFIED_HTTP_METHOD` cases since the API is being deliberately abused.

There is no statement/branch coverage of the system under test — Schemathesis is a black-box tool, the only "coverage" it measures is over its own input space.

## 9. What's genuinely novel at the code level

The **two-channel negative generator** (`specs/openapi/negative/__init__.py:300-355`) is unusual: instead of only mutating the *schema* and asking `hypothesis-jsonschema` to draw from the mutated schema, it also takes a freshly-drawn *valid* body, walks `collect_value_targets` to find positions that can be made schema-violating, and surgically applies an in-place violation (`apply_value_channel`) — re-validating with `real_validator` (`:322`) to discard mutations a permissive sibling schema would silently re-accept. This catches the false-negative class where pure schema-level mutation produces values that another `oneOf` branch happens to validate. The **heuristic Link inferencer** (`specs/openapi/stateful/inference.py`) that mounts a full Werkzeug routing `Map` over all operation paths and consumes `Location` response headers to chain CRUD operations even when the spec ships no `links` block is also distinctive — it turns stateful testing from an opt-in spec feature into a default capability. Finally, the **layered scheduler** (`engine/run/unit/_layered_scheduler.py:16`) treats schema-derived operation dependencies as a DAG of layers and dispatches them in order, so that POST-creating operations run before GET/DELETE that depend on their outputs — a static scheduling decision that very few fuzzers expose.
