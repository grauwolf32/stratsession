# SmokedMeat — code-level analysis (architecture focus)

Source: `sources/ci-cd/smokedmeat/` (Boost Security Labs, AGPL-3.0, Go 1.26). The feature/capability surface is covered in [`../ci-cd-security.md`](../ci-cd-security.md) and the upstream README; this report focuses on **architecture, transport, persistence, and engineering choices**. Per-vector exploitation primitives are intentionally not detailed here.

## Architecture overview — three components, NATS-mediated

The repository declares three `cmd/` binaries that compose into one engagement-time framework:

| Binary | Role | Source |
|---|---|---|
| `cmd/counter/` | Operator TUI (Bubbletea v2) — drives engagement workflow, renders the attack graph viewer | `internal/counter/` |
| `cmd/kitchen/` | C2 teamserver — HTTP/WebSocket front end, NATS JetStream message bus, BBolt persistence | `internal/kitchen/` |
| `cmd/brisket/` | Agent dropped on the runner — beacons / executes orders from Kitchen | `internal/brisket/` |

The data flow is:

```
Counter (operator)  <—WebSocket—>  Kitchen (teamserver)  <—NATS JetStream—>  Brisket (agent on runner)
                                          ↓
                                  BBolt persistence
                                  (orders, agents, sessions, pantry, history, ...)
                                          ↓
                                  Browser /graph view
                                  (Cytoscape.js over WS)
```

Auth between Counter and Kitchen is **SSH-key challenge** (`POST /auth/challenge` → `POST /auth/verify`, `internal/kitchen/server.go:259-260`), with rate-limiter middleware on the challenge endpoint. Every other endpoint is wrapped in an `opAuth` middleware (`server.go:271`+).

The codebase has a substantial test surface: most files have a `*_test.go` companion (e.g. `internal/pantry/` ships 11 source files + 6 test files for ~6.6k LOC total). This is a production-quality Go project, not research-grade scaffolding.

## Module layout — `internal/` packages

```
internal/
  bashctx/      — bash context utilities
  brisket/      — agent runtime (35 source/test files; one per capability)
  buildinfo/    — build metadata
  cachepoison/  — GHA Actions Cache poisoning primitives
  counter/      — operator TUI logic
    tui/        — subject-based file split (update.go, view.go, model.go, …)
  gitleaks/     — embedded gitleaks scanner with custom rules
  gump/         — /proc memory scanning for runner secret recovery
  kitchen/      — teamserver
    agents/     — Brisket-side beaconing protocol on the server side
    auth/       — SSH challenge/verify
    db/         — BBolt schemas
  lotp/         — "Living Off The Pipeline" payload catalog
  models/       — shared types (Order, Coleslaw, ScanResult, etc.)
  pantry/       — attack-graph data structure
  pass/         — NATS JetStream abstractions
  poutine/      — embedded poutine SAST wrapper
  rye/          — injection-context bookkeeping
  stagerurl/    — stager URL generator
```

## Key data structures (`internal/models/`)

The wire types are deliberately small. Each is JSON-marshallable for NATS payloads and has round-trip tests:

- **`Order`** (`internal/models/order.go`) — command from Kitchen to a specific Brisket agent. Carries an ID, the target agent ID, and the command payload.
- **`Coleslaw`** (`internal/models/coleslaw.go`) — response from Brisket. `NewColeslaw(orderID, sessionID, agentID)` + `SetOutput(stdout, stderr []byte, exitCode int)` + `SetError(err)`. `Success() bool` derives from exit code. Output is byte-slice (not string) — handles non-UTF-8 cleanly.
- **`ScanResult`** + `ScanFinding` + `ScanRule` (`internal/models/scan.go`) — output of the embedded poutine/gitleaks scans, with `HasFindings() / HasCritical() / HasHigh()` predicates and a `FormatOutput()` for the TUI.
- **`CachePoisonStatus`** (`internal/models/cache_poison.go`), **`CloudQueryResult`** (`internal/models/cloud_query.go`), **`PivotResult`** (`internal/models/pivot.go`) — typed result envelopes for the corresponding subsystems.

The models package has no business logic — just types + marshal/unmarshal + simple state methods. This makes it the safe import target for both Brisket and Kitchen (which otherwise share little).

## NATS subject layout (`internal/pass/`)

Three top-level subjects:

```go
SubjectOrdersPrefix   = "smokedmeat.orders"
SubjectColeslawPrefix = "smokedmeat.coleslaw"
SubjectBeaconPrefix   = "smokedmeat.beacon"
```

Full subjects are namespaced per agent ID: `smokedmeat.orders.<agent_id>` (Kitchen → Brisket), `smokedmeat.coleslaw.<agent_id>` (Brisket → Kitchen), `smokedmeat.beacon.<agent_id>` (Brisket heartbeat → Kitchen). JetStream's `FilterSubject` is used to subscribe per agent (`assert.Equal(t, "smokedmeat.orders.info-test", info.Config.FilterSubject)` in the tests confirms this). Single backend (NATS JetStream from `github.com/nats-io/nats.go v1.38.0`) handles message durability — Kitchen does not implement its own message store for transport.

## BBolt schema (`internal/kitchen/db/`)

Single-file BBolt database with **nine top-level buckets** declared in `db.go`:

```go
BucketMeta          = []byte("meta")           // schema version + run metadata
BucketOrders        = []byte("orders")          // outstanding/completed orders
BucketAgents        = []byte("agents")          // registered Brisket instances
BucketSessions      = []byte("sessions")        // operator sessions
BucketStagers       = []byte("stagers")         // stager URL registrations
BucketMetrics       = []byte("metrics")         // op metrics
BucketPantry        = []byte("pantry")          // serialized attack graph
BucketHistory       = []byte("history")         // operation log
BucketKnownEntities = []byte("known_entities")  // de-dup tracking across analyses
BucketLoot          = []byte("loot")            // captured artifacts
```

`UnknownBuckets` is tracked at open time — if the on-disk DB has buckets the running binary doesn't recognize, that's flagged in an `UnknownBuckets` field rather than silently dropped. The codebase has explicit schema-version policy documented in `CLAUDE.md` (not for me to follow, but it does describe the on-disk contract): start at schema 1.0, additive minor bumps for new buckets / optional fields, major bumps when older binaries can't safely read the new layout. Schema version lives in `BucketMeta`.

`loot.go` has a `deleteLootConflicts(b *bolt.Bucket, entry *LootRow) error` helper — loot dedup happens at write time, not at read time, which keeps the read path simple.

## Pantry — the attack-graph data structure

`internal/pantry/` (6.6k LOC across 17 files, ~half tests). Built on `github.com/hmdsefi/gograph v0.7.0`. The public API on `*Pantry` (from `graph.go`):

```go
AddAsset(asset Asset) error
AddRelationship(fromID, toID string, rel Relationship) error
RemoveAsset(id string) error / RemoveRelationship(fromID, toID string) error
GetAsset(id string) (Asset, error) / HasAsset(id string) bool
GetAssetsByType(assetType AssetType) []Asset
GetNeighbors(id string, hops int) ([]Asset, error)
AllAssets() []Asset / AllRelationships() []Edge
Size() int / EdgeCount() int / Version() int64
UpdateAssetState(id string, state AssetState) error
FindVulnerabilities() / FindSecrets() / FindHighValueTargets() []Asset
GetAttackPaths(sourceID string, targetTypes []AssetType) [][]Asset
```

Asset taxonomy (`internal/pantry/assets.go`):

| `AssetType` | Meaning |
|---|---|
| `organization` | GitHub org |
| `repository` | Repo within an org |
| `workflow` | GitHub Actions workflow file |
| `job` | Job within a workflow |
| `self_hosted_runner_target` | Identified self-hosted runner |
| `secret` | Secret recovered/identified |
| `token` | API/access token |
| `cloud` | Cloud resource (AWS/GCP/Azure/K8s) |
| `agent` | A running Brisket |
| `vulnerability` | Pipeline vuln finding (from poutine) |

`Version() int64` increments on every mutation — the browser graph view uses this for cheap "should I re-render" checks (HTTP polling pattern, not full diff). `GetAttackPaths(sourceID, targetTypes)` returns `[][]Asset` — pure pathfinding, no extra metadata. The `killchain.go` / `pivot_rules.go` / `poutine.go` / `relationships.go` / `self_hosted_runner.go` companion files contain domain-specific *interpreters* on top of the generic graph (which assets connect to which under what relationship, how to map poutine SAST output into graph nodes, etc.). Splitting graph mechanics from domain semantics keeps both testable in isolation — each has a `_test.go`.

## Kitchen HTTP surface

The teamserver exposes a flat HTTP router (`internal/kitchen/server.go`). Categories:

| Category | Endpoints |
|---|---|
| Auth | `POST /auth/challenge` (rate-limited middleware), `POST /auth/verify` |
| Health | `GET /health` (public, no auth) |
| Operator UI | `GET /` (homepage), `GET /ws` (WebSocket for operator session) |
| Analysis | `POST /analyze`, `GET /analyze/result/{analysisID}` |
| GitHub API proxy | `POST /github/repos`, `/github/repos/info`, `/github/workflows`, `/github/workflow-runs`, `/github/user`, `/github/token/info`, `/github/app/installations`, `/github/app/token` |
| Deployment ops | `POST /github/deploy/{pr,issue,comment,lotp,dispatch,preflight,self-hosted-callback-pr,self-hosted-workflow-push}` |
| Cache poison | `POST /cache-poison/prepare` |
| Pantry (graph) | `GET /pantry` (data), separate WS for live updates |
| History | `GET /history`, `POST /history` |
| Lifecycle | `POST /purge` |
| Callbacks | `GET /callbacks`, `POST /callbacks/{callbackID}` |

Every non-auth, non-health endpoint is wrapped in `opAuth(http.HandlerFunc(...))` middleware. The GitHub proxy endpoints exist so the operator's GitHub PAT can stay on the server — Counter never sees the raw token, only the proxy's API responses. This is a deliberate operator-security choice and is one of the few places where the architecture is opinionated rather than mechanical.

WebSocket transport: `github.com/coder/websocket v1.8.14` (modern replacement for gorilla/websocket). The operator session WS at `/ws` carries event streams; a separate WS hub (`internal/kitchen/graph_hub.go` + `graph_ws.go`) handles live graph updates to browser clients.

## Brisket — agent runtime

35 files under `internal/brisket/`, each one a feature module with its own test. Notable architectural patterns:

- **Platform-gated implementations** via build tags: `resident_linux.go` + `resident_linux_test.go` + `resident_unsupported.go` (so the Linux-only `/proc`-scanning path doesn't break the Windows/macOS build).
- **One file per primitive** — `agent.go`, `cache_poison.go`, `cloud_query.go`, `inject.go`, `memdump.go`, `oidc_aws.go`/`oidc_azure.go`/`oidc_gcp.go`/`oidc_k8s.go` (one per cloud), `recon.go`, `scanner.go`, `token_tester.go`, `transfer.go`. Each is small and independently testable.
- **`testutil_test.go`** provides shared test fixtures — a common pattern in this codebase.

Cloud OIDC modules are split per provider (not unified into a generic OIDC abstraction) because each cloud's token-exchange protocol has materially different request shapes — the per-provider split is the right size of abstraction for ~200 lines each.

## Counter — operator TUI

`internal/counter/` orchestrates the operator workflow. Files outside `tui/`: `client.go` (Kitchen HTTP/WS client), `nats.go` (direct NATS subscriber for live events that don't need to round-trip Kitchen), `sshauth.go` (Counter side of the SSH challenge), `scanner.go`, `cache_poison.go`, `callbacks.go`, `purge.go`, `versioncheck.go`, `names.go` (random names for generated stagers).

`internal/counter/tui/` is split by *subject* rather than by Bubbletea convention — separate files for `setup.go` (wizard), `wizard.go` (exploit), `deploy.go`, `command.go`, `kitchen.go` (server-side WS), `agent.go` (beacon/coleslaw handling), `analysis.go`, `model.go`, `messages.go`, `view.go`, `helpers.go`, `token.go`, `pivot.go`, `tree.go`, `suggestions.go`. New logic goes in its subject file, not in a monolithic `update.go` — explicit policy. This avoids the common Bubbletea anti-pattern of one giant `Update()` switch.

UI stack: **Bubbletea v2** (`charm.land/bubbletea/v2`), **Lipgloss v2** (`charm.land/lipgloss/v2`), **Ultraviolet** (`charm.land/ultraviolet`) for layout + ANSI-safe screen compositing. Ultraviolet is the layout library; modals use `uv.ScreenBuffer` for compositing instead of manual line-by-line overlays.

## External dependencies of note (`go.mod`)

| Choice | Why interesting |
|---|---|
| **`github.com/boostsecurityio/poutine v1.1.3`** | Same vendor's pipeline-SAST scanner, embedded as a library — the recon engine is in-process, not subprocess'd. Reduces install steps but couples the SmokedMeat version to a poutine release. |
| **`github.com/zricethezav/gitleaks/v8 v8.30.0`** | Gitleaks as a library, not via CLI exec. SmokedMeat ships its own custom rules. |
| **`github.com/nats-io/nats.go v1.38.0`** + **`testcontainers/testcontainers-go/modules/nats v0.40.0`** | NATS as the message bus; testcontainers used to spin up a real NATS in tests rather than mocking. |
| **`go.etcd.io/bbolt v1.4.3`** | Embedded KV; no external DB dependency for the teamserver. |
| **`github.com/hmdsefi/gograph v0.7.0`** | The graph library underlying Pantry. Niche choice — most Go projects roll their own. |
| **`github.com/coder/websocket v1.8.14`** | Modern WebSocket library, replaced gorilla/websocket. |
| **`charm.land/bubbletea/v2`** + **`charm.land/lipgloss/v2`** + **`charm.land/ultraviolet`** | Charm's next-generation TUI stack (the "charm.land" import path is the v2 migration). Pre-release versions pinned. |
| **`github.com/lestrrat-go/jwx/v3 v3.0.13`** | JWT / JWS for the GitHub App PEM → installation-token exchange. |
| **`github.com/fatih/semgroup v1.3.0`** | Semaphore-limited error group — for bounded concurrent fan-out. |
| **`github.com/google/go-github/v59`** | GitHub REST client. |
| **AWS SDK v2 + Azure SDK + Google Cloud SDK** | All three cloud SDKs are direct deps — the OIDC pivot subsystem talks to STS/AAD/STS-GCP natively rather than shelling out to provider CLIs. |
| **`github.com/atotto/clipboard v0.1.4`** | TUI clipboard integration for copying generated payloads / stager URLs. |

The dep set is large but every entry is justified by a concrete subsystem — there's no "vestigial library brought in by a transitive dependency hijacking the import path" pattern. The pinning of Charm's bubbletea/lipgloss/ultraviolet at pre-release versions is the only fragile piece (the README acknowledges Bubbletea v2 is still RC).

## What's genuinely novel at the code level

1. **Subject-based TUI file organization (`internal/counter/tui/`)** is the right answer to the Bubbletea-update.go-grows-forever problem. Most Bubbletea projects above ~3k LOC of UI code drown in a single `Update()` switch. SmokedMeat enforces the split as policy and the codebase stays readable.

2. **Embedding poutine and gitleaks as libraries** rather than subprocess'ing them means the framework can pass typed objects through the pipeline (no JSON re-parsing) and ship as a single binary. This is the right architectural choice when you control both sides of the dependency — the cost is version coupling, the benefit is operator simplicity.

3. **NATS subject layout per agent ID** (`smokedmeat.{orders,coleslaw,beacon}.<agent_id>`) with JetStream `FilterSubject` subscriptions cleanly maps to multi-operator / multi-agent semantics. Each Brisket only sees its own orders; Kitchen demultiplexes by subject suffix. This is canonical NATS usage and is much simpler than rolling per-agent connection state.

4. **Pantry = generic graph + domain interpreters** (graph mechanics in `graph.go`, kill-chain / pivot-rules / poutine-mapping in separate files) keeps both halves testable in isolation. The `Version() int64` monotonic counter on mutations is a low-effort optimization that lets the WS hub do dirty-bit checks without diffing.

5. **Explicit BBolt schema versioning policy** (declared in repo docs, enforced via `BucketMeta` + `UnknownBuckets` tracking) — most Go OSS projects discover schema-version pain after they ship; SmokedMeat declares the policy up front (when to bump major / minor / not bump). The pattern is worth borrowing.

The codebase quality is consistent with Boost Security Labs' commercial product engineering — it does not read like research scaffolding. For a defender evaluating whether to use SmokedMeat as a sandbox tabletop substrate, the engineering quality lowers the operational risk meaningfully.
