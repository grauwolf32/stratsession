# Cherrybomb — code-level analysis

## 1. Architecture overview

Cherrybomb is a Rust CLI compiled to a single binary that consumes an OpenAPI document and emits design-flaw and runtime alerts. The root `Cargo.toml` (`Cargo.toml:1-34`) declares a binary crate `cherrybomb` that depends on two in-repo path crates, forming a three-crate Cargo workspace by composition rather than `[workspace]` declaration:

- `cherrybomb` (CLI) — `src/main.rs`, `src/options.rs`, `src/table.rs`, `src/telemetry.rs`.
- `cherrybomb-engine` (`cherrybomb-engine/Cargo.toml:1-28`) — scan orchestration, rule implementations, HTTP attack client.
- `cherrybomb-oas` (`cherrybomb-oas/Cargo.toml:1-23`) — OAS struct definitions and ref-resolution helpers.

`main.rs` parses CLI args with `clap` (`src/main.rs:6-12`), optionally loads a JSON/YAML config (`src/main.rs:14-41`), then invokes `cherrybomb_engine::run(&mut config)` (`src/main.rs:77`) under a `#[tokio::main]` runtime. Results come back as a `serde_json::Value` and are rendered by `print_tables` (`src/table.rs:66-99`). Exit code `101` is returned when any check has alerts, `0` otherwise (`src/table.rs:94-98`).

## 2. Module / crate layout

- `cherrybomb-oas/src/legacy/` — `legacy_oas.rs` (top-level OAS structs and the `OAS` trait), `path.rs` (`PathItem`, `Operation`), `param.rs`, `schema.rs`, `refs.rs` ($ref resolution), `utils.rs` (`Method` enum, helpers). The crate's `lib.rs` (`cherrybomb-oas/src/lib.rs:1-3`) re-exports only the `legacy` module; `oas.rs` is empty.
- `cherrybomb-engine/src/info/` — read-only "Info" profile: `eps.rs` (endpoint table) and `params.rs` (parameter table) build summary views used by `run_profile_info` (`cherrybomb-engine/src/lib.rs:88-114`).
- `cherrybomb-engine/src/scan/` — split into `passive/` (spec-only audits) and `active/` (HTTP probes), plus `checks.rs` (rule registry), `macros.rs` (rule-declaration macros), `scan.rs` (shared `Alert`/`Level`/`Certainty` types at `cherrybomb-engine/src/scan.rs:8-50`).
- `cherrybomb-engine/src/config.rs` — `Profile` enum (`Info`/`Normal`/`Active`/`Passive`/`Full`/`OWASP`, the last is `todo!()`) and `Config` struct used by both the CLI and engine.

## 3. OpenAPI spec parsing

Cherrybomb does **not** use `openapiv3` or `oas3` crates. The entire OAS schema is hand-rolled with `serde::Deserialize` derives in `cherrybomb-oas/src/legacy/legacy_oas.rs` (e.g. `Info`, `Server`, `Components`, `SecScheme`, `OAuthFlows` at lines 8-176). A common behavioural surface is exposed through the `OAS` trait (`cherrybomb-oas/src/legacy/legacy_oas.rs:203-212`) implemented by two structs:

- `Swagger` (`legacy_oas.rs:213-224`) — `openapi: String`, paths required. Intended for OAS 3.0.
- `OAS3_1` (`legacy_oas.rs:225-237`) — adds `webhooks: Option<Paths>`; its `get_paths()` merges paths and webhooks (`legacy_oas.rs:265-274`).

The actual engine only ever instantiates `OAS3_1` (`cherrybomb-engine/src/lib.rs:55-58`), so **Swagger 2.0 is unsupported** and the `Swagger` struct is dead code at runtime. Input may be JSON or YAML (`cherrybomb-engine/src/lib.rs:38-54`); YAML is parsed via `serde_yaml` then re-funnelled through `serde_json::from_value`. `$ref` resolution lives in `cherrybomb-oas/src/legacy/refs.rs` and is invoked lazily through `.inner(&swagger_value)` calls on `SchemaRef`, `ParamRef`, `ResponseRef` etc.

## 4. Audit rule set

Rules split into **passive** (24 spec audits, declared in `cherrybomb-engine/src/scan/checks.rs:65-93`) and **active** (15 HTTP probes, `checks.rs:95-201`). Each passive rule is a method returning `Vec<Alert>`. Four representative examples:

**`check_fn_auth` — per-operation auth presence** (`scan/passive/auth.rs:68-117`). Walks every `(path, method, operation)`, collects security requirement keys, raises `Medium` if empty and `Medium` if a referenced scheme is missing from `components.securitySchemes`; raises `High` if the scheme is HTTP `basic`:
```rust
if secs.is_empty() { alerts.push(Alert::new(Level::Medium,
    "Endpoint does not use any security scheme", ...)); }
```

**`check_arr_attrs` — unbounded arrays** (`scan/passive/type_checks.rs:79-99`). Resolves every `array`-typed schema via `get_schemas_by_type` and alerts `Low` for missing `maxItems`, `Info` for missing `minItems` — i.e. catches the "unbounded array" DoS class.

**`check_successes` — missing 2xx** (`scan/passive/general.rs:47-71`). Parses every response key, raises `Low` "Responses have no success status(2XX)" if none of the response codes parse into `200..300`.

**`check_method_permissions` — verb/scope mismatch** (`scan/passive/additions_checks.rs:194-271`). Splits by HTTP method: `get_check` requires every OAuth scope on a `GET` op to start with `read`, `put_check` requires `write`, `post_check` requires `write:` or `read:` — a heuristic for unsafe verb/scope pairing.

Other notable passive rules: `check_401`/`check_403` (`scan/passive/auth.rs:16-41`) — flag operations with `security` defined but missing 401/403 responses; `check_unused_schema` (`scan/passive/general.rs:137-155`) — string-searches the serialised spec for `#/components/schemas/{name}` references; `check_int_type` (`scan/passive/additions_checks.rs:39-167`) — cross-validates `format` (`int32`/`int64`/`float`/`double`) against the declared `type`; `check_valid_encoding` (`additions_checks.rs:286-308`) — gates request content-types against a hard-coded list of 35 MIME types (`additions_checks.rs:349-385`).

Active rules live in `scan/active/additional_checks.rs` (1249 lines) — examples: `check_open_redirect` (l. 577) injects `http://www.google.com` into any query param whose name matches a redirect list; `check_string_length_max` (l. 625) sends a `B`/`L`/`S`/`T`-padded string of `maxLength` bytes; `check_min_max` (l. 697); `check_broken_object_level_authorization` (l. 829); `check_ssl` (l. 907) attempts a plain-HTTP request and alerts if any 2xx comes back; `check_sqli` (l. 23) injects `'`, `"`, `` ` ``, `%00`, `' OR '1` into params whose name matches `*id*` or a SQLi-prone-name list.

## 5. Rule engine

Rule registration is a macro-based DSL in `cherrybomb-engine/src/scan/macros.rs`. `impl_passive_checks!` (`macros.rs:1-58`) takes tuples of `(EnumVariant, check_function, "NAME", "description")` and expands into:

1. An `enum PassiveChecks { CheckServerUrl(Vec<Alert>), ... }` carrying its own results (`macros.rs:5-9`), deriving `EnumIter` from `strum_macros`.
2. `from_string`, `name`, `description`, `inner`, `create_checks` impls (`macros.rs:11-46`).
3. A blanket `impl<T: OAS+Serialize> PassiveSwaggerScan<T> { fn run_check(&self, check) }` that dispatches each variant to its registered method (`macros.rs:48-56`).

`impl_active_checks!` (`macros.rs:60-117`) is analogous but carries `(Vec<Alert>, AttackLog)` and additionally takes a `$response_func` (`is_2xx`/`is_3xx`/`reflected_and_2xx`/`ssrf_and_2xx`) that classifies HTTP outcomes into alerts (`scan/active/response_checks.rs:7-97`).

The actual rule traits live alongside each subsystem — `PassiveAuthScan` (`scan/passive/auth.rs:8-13`), `PassiveTypeScan` (`scan/passive/type_checks.rs:6-11`), `PassiveGeneralScan` (`scan/passive/general.rs:7-18`) — and are implemented as `impl<T: OAS + Serialize> Trait for PassiveSwaggerScan<T>`. So a rule = trait method returning `Vec<Alert>`; the macro just wires it into the registry. Run loop: `PassiveSwaggerScan::run` (`scan/passive/passive_scanner.rs:45-58`) iterates either the full `PassiveChecks::iter()` set or a `Partial(Vec)` list. `ActiveScan::run` (`scan/active/active_scanner.rs:86-111`) is the async equivalent and additionally calls `Self::create_hash` to pre-resolve path parameters before probing.

Severity tagging uses `Level::{Info,Low,Medium,High,Critical}` (`scan/scan.rs:8-15`) and `Certainty::{Passive,Low,Medium,High,Certain}` (`scan/scan.rs:22-29`); passive findings default to `Certainty::Passive`, active findings derive certainty from the response-classifier (e.g. an open redirect with a real 3xx becomes `Certainty::Certain`, `response_checks.rs:24-37`).

## 6. Output

Two formats — `Json` and `Table` (`src/options.rs:62-67`); the README's mentions of other formats are aspirational. `print_tables` (`src/table.rs:66-99`) dispatches: JSON dumps the raw `serde_json::Value` to stdout and optionally writes a file; Table mode renders four `comfy-table` tables — passive alerts, active alerts (both via `print_full_alert_table` at `src/table.rs:207-237` with columns Check / Severity / Description / Location), then param and endpoint inventories. **No SARIF, no JUnit, no HTML output** — `grep` for `sarif` returns nothing.

## 7. CI/CD usage

The exit-code contract is minimal: `ExitCode::from(101)` if any alert was raised in either passive or active output, `ExitCode::SUCCESS` otherwise (`src/table.rs:94-98`). There is **no severity-threshold flag** — a single `Info` finding fails the build the same as a `Critical`. The only knobs are `--profile`, the `passive_include`/`passive_exclude`/`active_include`/`active_exclude` config lists (`cherrybomb-engine/src/config.rs:20-46`), `--ignore-tls-errors`, `--server` override, and `--no-telemetry` (`src/options.rs:9-54`). The merge logic between CLI and config file is in `src/main.rs:43-62`.

## 8. What is genuinely novel at the code level

The interesting contribution is the **macro-generated rule registry that treats spec lint and HTTP probe as two parallel state machines over the same `OAS` trait**: a passive rule is a pure function `&PassiveSwaggerScan<T> -> Vec<Alert>`, an active rule is an async function returning `CheckRetVal` plus a separately-declared classifier (`is_2xx`/`reflected_and_2xx`/`ssrf_and_2xx`) — so the same `impl_active_checks!` line declares both the attack and how to interpret the answer (`scan/checks.rs:97-201`, `scan/active/response_checks.rs:1-97`). The split makes adding a rule a one-line registry edit plus one trait method.

Conceptually, Cherrybomb's passive checks attack a different layer than Schemathesis: where Schemathesis derives Hypothesis strategies from the schema and looks for runtime contract violations, Cherrybomb's passive scanner inspects the spec as a document — flagging missing `401`/`403` responses (`scan/passive/auth.rs:16-41`), unbounded arrays/strings (`scan/passive/type_checks.rs:79-99`), `basic` auth (`scan/passive/auth.rs:48-56`), unused schemas (`scan/passive/general.rs:137-155`), and verb/scope mismatches (`scan/passive/additions_checks.rs:258-271`). These findings are reachable in CI without ever sending a request, complementing rather than overlapping with fuzz-based runtime checks.

Caveats worth flagging for the brief: the `Swagger`/OAS-3.0 struct exists but is unwired (engine uses `OAS3_1` exclusively, `cherrybomb-engine/src/lib.rs:55`); `Profile::OWASP` is `todo!()` (`cherrybomb-engine/src/lib.rs:84`); `check_unused_schema` is a substring search on the serialised JSON rather than a real reference graph; and exit-code granularity is binary.
