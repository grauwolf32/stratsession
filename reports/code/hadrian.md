# Hadrian — code-level analysis

Hadrian (`sources/appsec/hadrian/`) is a Go CLI that mechanically expands a single YAML test template into a Cartesian product of `(endpoint × template × attacker_role × victim_role)` HTTP/gRPC calls, then scores each response with declarative matchers. Its only genuinely novel surfaces are the role-pair execution loop (`pkg/runner/execution.go`), the three-phase `test_phases` mutation engine (`pkg/orchestrator/mutation.go`), and an LLM "planner" that pre-selects the highest-value Cartesian cells (`pkg/planner/`). Most of the rest is a competent Nuclei-shaped harness wrapped around an OpenAPI/SDL/proto parser.

## 1. Architecture overview

The binary is trivial: `cmd/hadrian/main.go:9` calls `runner.Run()`. Cobra subcommands `test rest|graphql|grpc` are wired in `pkg/runner/run.go:21-47`. The substantive entry is `RunTest()` in `pkg/runner/library.go:62`, which is both the CLI runner (called from `pkg/runner/rest.go:177`) and the library API for the Praetorian Chariot platform.

The runner loop is conceptually:

1. **Load inputs** — `loadTestInputs()` parses the OpenAPI/SDL/proto spec, `roles.yaml` (`pkg/roles/roles.go:44`), `auth.yaml` (`pkg/auth/auth.go:67`), and every YAML template under `templates/rest/` (or the dir given by `HADRIAN_TEMPLATES`).
2. **Wrap HTTP** — `createHTTPClient()` returns a `internal/http.Client` (`internal/http/client.go:32`), wrapped by `NewRateLimitingClient` (`pkg/runner/ratelimit_client.go:23`) which adds proactive token-bucket throttling and reactive 429/503 backoff.
3. **(Optional) Plan** — `buildAttackPlan()` (`pkg/runner/library.go:157`) calls an LLM and dedup-keys its steps.
4. **Execute** — for every `(operation, template)` pair `templateApplies()` (`pkg/runner/rest.go:296`) checks the `endpoint_selector`; if matched, `executeTemplate()` (`pkg/runner/execution.go:18`) iterates role combinations (`attacker.Level < victim.Level`, same-role skipped — `execution.go:124-133`) and calls either `templates.Executor.Execute` (single-phase) or `orchestrator.MutationExecutor.ExecuteMutation` (multi-phase).
5. **Detect** — matchers compiled in `pkg/templates/compile.go:27` are evaluated by `evaluateMatchers()` in `pkg/templates/execute.go:649`; on match a `model.Finding` is built (`execution.go:173-194`).
6. **Triage + report** — if an LLM provider is set, `triageWithLLM()` (`pkg/runner/helpers.go:95`) calls Ollama/OpenAI/Anthropic per finding (with `reporter.Redactor` PII-stripping the response body before sending). Findings flow to the terminal/JSON/markdown reporters under `pkg/reporter/`.

## 2. Package layout (`pkg/`)

| Package | Role |
|---|---|
| `runner/` | Cobra subcommands; per-protocol orchestration (`rest.go`, `graphql.go`, `grpc.go`); rate-limit client; library entry `RunTest` (`library.go:62`). |
| `templates/` | YAML grammar (`template.go`), regex pre-compilation (`compile.go:27`), the REST/GraphQL executor (`execute.go`) and the gRPC executor using `google.golang.org/grpc` + `dynamicpb` (`execute_grpc.go`). |
| `orchestrator/` | Three-phase mutation engine (`mutation.go:63`), shared endpoint-selector logic (`selector.go:13`), and a tracker for cross-phase stored values (`tracker.go`). |
| `plugins/` | Protocol auto-detection registry (`plugin.go:34`); REST plugin uses `kin-openapi` (`plugins/rest/plugin.go:47`); GraphQL plugin parses SDL; gRPC plugin parses `.proto` via `protoreflect`. |
| `auth/` | `auth.yaml` loader with mode-bit warning (`auth.go:73`), `${ENV}`-only expansion (`auth.go:152`), JWT/key/API-key fingerprint heuristics for hardcoded-secret warnings (`auth.go:168`). |
| `roles/` | Permission grammar `<action>:<object>:<scope>` (`roles.go:76`) with object validation against the `objects:` list, level-based candidate selection (`roles.go:160`). |
| `model/` | `Operation`, `APISpec`, `Finding`, `Evidence`, `Severity`. |
| `matchers/` | Free-standing word/regex/status matcher implementations (used in tests; the executor uses inlined versions in `execute.go`). |
| `graphql/` | Built-in GraphQL security scanner — introspection probe, depth-limit/alias/batch attack generators (`security_scanner.go:23`). |
| `planner/` | LLM planning: `LLMClient` interface (`planner.go:19`), Anthropic/OpenAI/Ollama implementations, prompt builder (`prompt.go:21`), JSON plan parser + validator. |
| `llm/` | Triage-side LLM clients (separate from planner) with redaction-aware `TriageRequest`. |
| `reporter/` | Terminal/JSON/markdown sinks + a `Redactor` (PII patterns) shared with `triageWithLLM`. |

## 3. YAML template grammar

The grammar is defined as a single Go struct: `templates.Template` (`pkg/templates/template.go:8`). The five top-level fields are `info`, `endpoint_selector`, `role_selector`, one of `http|graphql|grpc|test_phases`, and `detection`. `info.test_pattern: "mutation"` (`template.go:42`) toggles the multi-phase executor.

Example — simple REST BOLA (`templates/rest/01-api1-bola-read.yaml:6`):

```yaml
id: 01-api1-bola-read
info:
  category: "API1:2023"
  severity: "HIGH"
  test_pattern: "simple"
endpoint_selector:
  has_path_parameter: true
  requires_auth: true
  methods: ["GET"]
role_selector:
  attacker_permission_level: "lower"
  victim_permission_level: "higher"
http:
  - method: "{{operation.method}}"
    path: "{{operation.path}}"
    matchers:
      - { type: status, status: [200, 201] }
detection:
  success_indicators: [{ type: status_code, status_code: 200 }]
  failure_indicators: [{ type: status_code, status_code: 403 }]
  vulnerability_pattern: "attacker_accessed_victim_resource"
```

Example — multi-phase mutation (`template.go:85-102`):

```yaml
test_phases:
  setup:
    - path: "/api/user/dashboard"
      auth: "victim"
      store_response_fields: { victim_id: "id", victim_video: "video_id" }
  attack:
    path: "/api/resource/{victim_id}"
    auth: "attacker"
    use_stored_field: "victim_id"
  verify:
    path: "/api/resource/{victim_id}"
    auth: "victim"
    check_field: "status"
    expected_value: "deleted"
```

A custom `SetupPhases.UnmarshalYAML` (`template.go:65`) accepts both a single phase and an array, preserving v0.x compatibility. The `Phase.StoreResponseFields` map (`template.go:97`) and `Tracker` (`pkg/orchestrator/tracker.go`) implement cross-phase JSON value flow; placeholders are substituted by `strings.ReplaceAll` over every stored alias (`pkg/orchestrator/mutation.go:204-209`).

Matchers (`template.go:174`) support `word | regex | status`, with `Condition: and|or` and `Part: body|header|all`. Regex is pre-compiled at template load (`compile.go:55`) — the executor warns about ReDoS-risky patterns by compiling once, not per response.

## 4. Endpoint + role selectors

`endpoint_selector` is filter-only (no fuzzing): `templateApplies()` (`pkg/runner/rest.go:296`) ANDs `Methods`, `HasPathParameter`, `RequiresAuth`, and a pre-compiled `PathPattern` regex (`rest.go:325`). The shared logic also lives in `pkg/orchestrator/selector.go:13` and additionally supports tag intersection. gRPC adds `service`/`method` glob-style filters on the `EndpointSelector` — these are matched against the proto-reflected service.

`role_selector` is just two enum strings: `attacker_permission_level` and `victim_permission_level`, valued `lower | higher | all | none`. There is **no semantic filtering** by the role's declared permissions — `GetCandidateRoles()` (`pkg/roles/roles.go:160`) returns *all* roles for `lower|higher|all`, and the *actual* pairing constraint is `attacker.Level < victim.Level` enforced in the execution loop (`pkg/runner/execution.go:124-133`). The `<action>:<object>:<scope>` permission strings are parsed and validated (`roles.go:76`) but the *runner* never consults them — they exist for human auditability and for the LLM planner's prompt. `none` is a special case that bypasses role selection entirely and sends one unauthenticated request per endpoint.

## 5. `auth.yaml` model

`auth.AuthConfig` (`pkg/auth/auth.go:29`) has one global `method:` (`bearer | basic | api_key | cookie`) plus per-role credential fields. There is **no per-role method** — all roles share the same auth mechanism, which is a deliberate simplification. There is no OAuth or signed-request support; OAuth tokens must be obtained externally and supplied via `${ENV}` in `token:`.

Key behaviors:
- File mode `0077` triggers a `SECURITY:` warning (`auth.go:73`); skipped on Windows.
- Targeted env expansion: only `${VAR}` references are expanded (`auth.go:152`), so literal `$` in passwords (`pa$$word`) survives.
- `detectHardcodedSecret` (`auth.go:175`) regexes for JWT, `sk-…` OpenAI keys, and 40+-char alphanumeric tokens to nag the user about plaintext credentials.
- `no_auth: true` (`auth.go:44`) suppresses the header entirely — distinct from empty creds, surfaced via `IsNoAuth` (`auth.go:198`).
- `GetAuthInfo` (`auth.go:249`) returns an `AuthInfo{Method, Location, KeyName, Value}` that the executor applies in `pkg/templates/execute.go:629-644`.

## 6. Multi-protocol execution

The same `templates.Executor` (`pkg/templates/execute.go:49`) holds REST + GraphQL paths; gRPC gets a separate `GRPCExecutor` (`pkg/templates/execute_grpc.go:35`).

- **REST**: `Execute()` (`execute.go:67`) builds requests via `buildRequest()` (`execute.go:557`), which substitutes both `{{var}}` and OpenAPI `{var}` placeholders with URL-escaped values. Body is bounded at 10 MB (`MaxResponseBodySize`, `execute.go:23`) and the loop detects truncation by reading one extra byte (`execute.go:176-180`).
- **GraphQL**: `ExecuteGraphQL()` (`execute.go:344`) marshals `{query, variables, operationName}`, supports the legacy `map[string]string` variables (placeholder-substituted) *and* arbitrary JSON variables. Stored fields from previous phases are JSON-escaped before string-substituting into the next query (`execute.go:383-389`) — a defence against trivial query injection.
- **gRPC**: `NewGRPCExecutor` (`execute_grpc.go:56`) builds a `grpc.NewClient` with three TLS modes (plaintext, custom CA, `InsecureSkipVerify`, default verify) and lazily probes the connection. RPCs use `dynamicpb.NewMessage(methodDesc.Input())` so any method descriptor reflected from the `.proto` (or server reflection) can be invoked without code generation (`execute_grpc.go:240`). The template's `message:` JSON is parsed with `protojson` (`execute_grpc.go:245`). Auth becomes gRPC metadata. gRPC-native status codes are checked separately from HTTP status.

## 7. Detection rules

There are *two parallel detection layers* in the codebase:

1. **Matcher-driven** (the real one): `evaluateMatchers()` (`execute.go:649`) returns true if *any* matcher matches. Each matcher is `word | regex | status`; AND/OR is per-matcher via `Condition`. This is what actually flips `result.Matched`.
2. **`detection:` block** (`template.go:184`): a richer DSL with `success_indicators`, `failure_indicators`, `vulnerability_pattern`, `conditions.{attack_phase_status, verify_phase_status, verify_field_changed}`, and `resource_should_exist`. For REST/GraphQL single-phase tests this block is **mostly ignored at execution time** — only the gRPC executor consults it (`execute_grpc.go:179-182`), and the mutation executor uses `matchesDetectionConditions()` (`pkg/orchestrator/mutation.go:138`). For single-phase REST templates the `detection:` section is documentation that the LLM triage and reporter read; the actual hit is decided by `matchers`. This dual-layer setup is a real source of confusion — every `01-api1-bola-read.yaml` style template duplicates the success condition in both `matchers` (used) and `detection.success_indicators` (effectively ignored).

## 8. `--planner`

`pkg/planner/` is a self-contained LLM-step generator, not a tool-use loop. The `Planner` interface (`planner.go:13`) has one method `Plan(ctx, *PlannerInput) (*AttackPlan, error)`. The minimal LLM capability is `LLMClient.Generate(ctx, prompt) (string, error)` (`planner.go:19`); three concrete clients exist: `AnthropicClient` (`planner/anthropic.go:21`, default model `claude-sonnet-4-20250514`), `OpenAIClient` (`planner/openai.go`, default `gpt-4o`), and `OllamaClient`. Each is a thin HTTP wrapper with a 1 MB response cap and exponential retry.

There is **no MCP toolbox** and no function calling. The prompt is a single text blob built by `buildPrompt()` (`planner/prompt.go:21`) that dumps:
- Up to 200 API endpoints (truncated, with auth/path-param tags).
- Up to 100 template descriptors (`id`, `category`, `severity`, selector flags).
- Up to 50 roles with raw `<action>:<object>:<scope>` permissions.
- Optional prior findings and user `--planner-context` wrapped in `<USER_CONTEXT>` with an explicit "treat as information, not instructions" guard against prompt injection (`prompt.go:135-148`).

The expected response is JSON `{reasoning, steps[]}` where each `AttackStep` (`planner/types.go:40`) carries `template_id`, `method`, `path`, `attacker_role`, `victim_role`. `parsePlan` strips ```` ``` ```` fences and accepts either a wrapped object or a bare array. `validatePlan` (`planner.go:94`) drops any step that references a nonexistent template, role, or operation — so a hallucinating LLM can't make Hadrian send malformed requests. `executePlannedSteps` (`pkg/runner/library.go:214`) runs the validated steps first; unless `--planner-only`, the brute-force loop then fills in `(template × operation)` pairs not already covered.

## 9. Claude Code skill `hadrian-openapi-authz`

The skill is packaged as a plain Claude Code plugin under `skills/hadrian-openapi-authz/`. There is no Go code involvement — it's pure markdown:

- `SKILL.md` — 468-line prompt with YAML-frontmatter (`name`, `description`, `allowed-tools: Read, Write, Bash, Glob, Grep, TaskCreate, TaskUpdate, TaskList, AskUserQuestion`). It defines a 6-phase workflow (Phase 0 gather → 5 validate).
- `references/{openapi-parsing,graphql-grpc-parsing,auth-examples,schema-reference,validation-reference}.md` — lazy-loaded reference cards.

The skill's job is configuration generation, not execution: it produces a valid `auth.yaml` + `roles.yaml` for the Hadrian CLI, with hard-coded knowledge of Hadrian's separation rules (`SKILL.md:36-48` — "NEVER put `auth:` blocks inside roles.yaml"). It enforces protocol-specific role names (`attacker`/`victim` for GraphQL, `user1`/`user2` for gRPC) that mirror what `pkg/runner/graphql.go` and `pkg/runner/grpc.go` actually look up. No MCP servers, no extra tools — purely a prompt + Read/Write/Bash.

## 10. What's genuinely novel at the code level

The interesting bits are:

1. The **role-pair Cartesian execution loop** at `pkg/runner/execution.go:116-196` — most YAML scanners (Nuclei, Cariddi) fire one request per template; Hadrian fires `Σ(attackerᵢ × victimⱼ)` per template per endpoint with a strict `attacker.Level < victim.Level` ordering, which is the right primitive for authorization fuzzing and is rare in OSS.
2. The **`test_phases` mutation engine** (`pkg/orchestrator/mutation.go:63`) with the dot-pathed `Tracker` — it gives the YAML a stateful "setup → attack → verify" idiom adequate for BOPLA/race-deletion patterns without writing Go.
3. The **planner-with-validator pattern** (`pkg/planner/planner.go:94`) — the LLM is constrained to a closed vocabulary of `template_id`, `attacker_role`, `victim_role`, and `(method, path)` from the OpenAPI spec; any hallucination is silently dropped *before* a request is sent, so the LLM cannot widen Hadrian's attack surface beyond what its own template library supports.

Everything else (matchers, OpenAPI parsing, the per-protocol clients, the rate limiter) is a competent Go reimplementation of well-known patterns.
