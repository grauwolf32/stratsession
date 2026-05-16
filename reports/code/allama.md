# Allama — code-level analysis

Source: `sources/defense/allama/` (submodule of stratsession). Repository was previously codenamed/forked; the `digitranslab/allama` package keeps namespaces such as `allama_ee` and `allama_registry` referenced from `pyproject.toml:79-95`.

> **Correction to the existing landscape brief:** the README / `reports/defensive-ops.md` describes Allama's sandbox as "WebAssembly Python sandbox." That's wrong. A repo-wide grep for `wasm|webassembly|pyodide|rustpython|wasi` returns zero matches — the actual implementation is **nsjail** (Linux user/mount/net/pid namespaces) with `cap_add: SYS_ADMIN` plus an AST-allowlist fallback. Detailed below.

## Architecture overview

Allama is a five-process distributed application packaged as one Docker image (`Dockerfile`) and orchestrated through `docker-compose.yml`:

1. **`api`** — FastAPI gateway (`allama.api.app:create_app`, `allama/api/app.py:289`) bound at `:8000`.
2. **`worker`** — Temporal worker for the DSL (workflow) loop, entrypoint `python -m allama.dsl.worker` (`docker-compose.yml:119`, `allama/dsl/worker.py:95`).
3. **`executor`** — Temporal worker for action execution inside an nsjail sandbox (`docker-compose.yml:131-184`, `allama/executor/worker.py`). Runs with `cap_add: SYS_ADMIN` + `seccomp:unconfined` (`docker-compose.yml:139-142`).
4. **`agent-executor`** — Temporal worker for LLM agent runs, uses pasta-based userspace networking inside nsjail (`docker-compose.yml:186-242`, `/dev/net/tun` passthrough on line 200).
5. **`ui`** — Next.js 15.5 frontend (`frontend/package.json:100`).

Backing services: PostgreSQL 16 for app state (`docker-compose.yml:264`), a separate PG 13 for Temporal history (`:298`), MinIO/S3 for blob storage (`:348`), Redis 7 for caching/leader election (`:366`), Caddy reverse proxy (`:6`). Temporal `auto-setup` 1.27.1 is the durable-execution backbone (`:310`). LiteLLM Proxy fronts every LLM call from the agent runtime and authenticates with JWTs minted by the agent executor (`allama/agent/gateway.py:1-22`).

Python 3.12+ project (`pyproject.toml:14`), AGPL-3.0 license, uv-based workspace with two internal packages: `allama-admin` (EE) and `allama-registry` (shared action SDK + tool catalog) (`pyproject.toml:98-99`).

## Module / package layout

- `allama/` — 50+ subpackages; the substantive ones are `api/` (FastAPI), `dsl/` (Temporal workflow engine), `executor/` (action sandbox glue), `agent/` (PydanticAI agent), `sandbox/` (nsjail wrapper + AST-validating Python "safe executor"), `integrations/` (OAuth providers), `db/`, `auth/`, `workflow/`, `cases/`, `secrets/`, `registry/`, `ee/`, `expressions/` (custom DSL evaluator using `lark==1.1.9`).
- `packages/allama-registry/` — Standalone Python package shipped to sandboxes. Contains 20 hand-written integration adapters in `allama_registry/integrations/` (e.g. `splunk.py`, `crowdstrike_falconpy.py`) plus 49 directories of YAML-defined "template tools" under `allama_registry/templates/tools/` (349 `.yml` files total) covering EDRs, SIEMs, threat-intel, ticketing, IAM, etc.
- `packages/allama-admin/` — EE workflows including `allama_ee/agent/workflows/durable.py:84` `DurableAgentWorkflow`.
- `alembic/versions/` — 121 migration scripts; config in `alembic.ini`, environment in `alembic/env.py`.
- `frontend/` — Next.js 15 + React 18 + TanStack Query + Radix UI + `@xyflow/react` (visual DAG editor).
- `docker/sandbox/Dockerfile` — minimal Python 3.12-slim rootfs that nsjail bind-mounts into the sandbox (`docker/sandbox/Dockerfile:4-32`).
- `deployments/helm/` and `deployments/terraform/` — production deployment scaffolding.

## FastAPI gateway

`create_app()` at `allama/api/app.py:289` is the factory. It registers ~50 routers — workflow management, workflow graph, executions, secrets, variables, schedules, cases, registry, agents, integrations, MCP, settings, webhooks, VCS sync, tables, custom fields, inbox, editor, admin (`allama/api/app.py:326-388`). A `lifespan` context (`:128`) ensures S3 buckets exist, spawns the platform-registry sync background task and pushes Temporal search attributes asynchronously (`:130-160`).

Auth is delegated to **fastapi-users 15.0.2** (`pyproject.toml:41`). The single authentication backend is cookie-transport + database-strategy (`allama/auth/users.py:534-538`), giving session-style auth backed by the `AccessToken` model (`allama/db/models.py:476`). Three login methods plug into that backend:

- **Basic** (email + password) — `fastapi_users.get_auth_router(auth_backend)` mounted only if `AuthType.BASIC` is enabled (`allama/api/app.py:390-410`).
- **Google OAuth2** — `GoogleOAuth2` client from `httpx-oauth`; `fastapi_users.get_oauth_router(...)` with `associate_by_email=True` (`allama/api/app.py:412-432`).
- **SAML 2.0** — custom router using `pysaml2 7.5.0` and `defusedxml`, `allama/auth/saml.py:1-46`. SAML responses are parsed by a hand-rolled `SAMLParser` (`:60`) and `SAMLRequestData` is persisted in PG (`allama/db/models.py:483`).

All three auth types are gated behind `require_auth_type_enabled` (`allama/auth/dependencies.py`) so an operator can disable any combination via `ALLAMA__AUTH_TYPES`. Three middlewares: `AuthorizationCacheMiddleware`, `RequestLoggingMiddleware`, and (non-dev) `SecurityHeadersMiddleware` (`:458-461`).

## Temporal workflow engine

This is the architectural backbone. The DSL workflow is **a single `@workflow.defn` class** `DSLWorkflow` at `allama/dsl/workflow.py:180` (1837 lines). All workflow-side imports are wrapped in `workflow.unsafe.imports_passed_through()` (`:23`) so they bypass Temporal's deterministic sandbox.

State that defines a workflow run — `dsl`, `dispatch_type`, `registry_lock`, `runtime_config`, `time_anchor`, `context`, `run_context`, `dep_list`, `scheduler` — is declared as instance attributes initialized inside `run()` (`:192-202`) because `@workflow.init` must be synchronous and cannot perform activity calls (comment at `:182-188`). Durability comes from Temporal automatically persisting the event history into its Postgres backend; on worker crash, replay re-derives all attribute state by re-executing pure code and replaying recorded activity results.

The workflow does virtually nothing CPU-bound itself — every non-deterministic operation is shipped to an activity. Examples of `workflow.execute_activity(...)` calls: `resolve_registry_lock_activity` (`:298`), `normalize_trigger_inputs_activity` (`:444`), `resolve_time_anchor_activity` as a local activity (`:492`), `parse_wait_until_activity` (`:605`), child-workflow spawn at `:793`. Retry behaviour is centralized in `RETRY_POLICIES["activity:fail_fast" | "activity:fail_slow"]` (`allama/dsl/common.py`).

Activities live in three places:

- `DSLActivities` class in `allama/dsl/action.py:322` — 15 `@activity.defn` methods (`:341-627`).
- `ExecutorActivities.execute_action_activity` in `allama/executor/activities.py:56-188` — runs on a separate task queue (`shared-action-queue`, set in `docker-compose.yml:166`). Wraps every user-action invocation, applies tenacity-driven `RateLimitExceeded` retries (`:101-105`), dispatches to the executor backend (`:111`), and **externalizes results to S3 via `get_object_storage().store(...)`** (`:124`) — this is what lets Allama survive Temporal's 4 MB payload limit on long fan-out workflows.
- Management/schedules/storage activities (`workflow/management/management.py:756`, `storage/collection.py:411`, `workflow/schedules/service.py:280`).

The worker entrypoint (`allama/dsl/worker.py:95`) builds a `SandboxedWorkflowRunner` with custom `passthrough_modules` for `allama`, `allama_ee`, `allama_registry`, `jsonpath_ng`, `dateparser`, `beartype` (`:44-75`), registers both `DSLWorkflow` and `DurableAgentWorkflow` (`:137`), and uses a `ThreadPoolExecutor(max_workers=100)` for activity dispatch (`:132-147`).

## PydanticAI agent layer

The agent layer wraps **`pydantic-ai-slim 1.29.0`** (`pyproject.toml:64`). Provider construction is centralized in `allama/agent/providers.py:7-16` (Anthropic, Bedrock, Google, OpenAI Chat + Responses, Ollama). The agent factory `build_agent()` lives at `allama/agent/factory.py:22-86`:

- Translates Allama tools to `pydantic_ai.tools.Tool` via `to_pydantic_ai_tools(...)` (`:15, :34`).
- Forces `parallel_tool_calls = False` when tools exist (OpenAI requirement, `:43-44`).
- Mounts MCP servers as `MCPServerStreamableHTTP` toolsets (`:58-65`).
- Routes `DeferredToolRequests` into the output union when any tool needs human approval (`:67-72`), tying into the EE `approvals_router`.

Tools are bound to the registry: `build_agent_tools` in `allama/agent/tools.py` resolves namespaces and registry actions, and `call_allama_action` (`tools.py:38-130`) spawns a **subprocess** (`allama.agent._subprocess_runner`) per tool call, exchanging input/output through temp-file JSON to bypass 64 KB pipe limits (`:62-86`).

LLM API calls go through a Allama-hosted LiteLLM proxy. `allama/agent/gateway.py` implements a `CustomLogger` plugin that authenticates each request via `verify_llm_token` (JWT) and resolves provider credentials per workspace via `AgentManagementService.get_provider_credentials(...)` (`gateway.py:32-46`). This is what makes the agent layer multi-tenant: secrets never leave the orchestrator process.

The durable agent loop itself is `DurableAgentWorkflow` at `packages/allama-admin/allama_ee/agent/workflows/durable.py:84`, an EE `@workflow.defn` that the DSL workflow invokes as a child workflow.

## Sandboxing (nsjail, NOT WebAssembly)

A repo-wide grep for `wasm|webassembly|pyodide|rustpython|wasi` returns zero matches. The implementation is **nsjail** (Linux namespaces) with an AST-validating fallback:

- **Primary sandbox: nsjail.** `allama/sandbox/executor.py:117` `NsjailExecutor` builds a protobuf config string (`_build_config`, `:139`) and runs `nsjail --config <cfg>` as a subprocess (`:359-378`). Isolation toggles: `clone_newnet`, `clone_newuser`, `clone_newns`, `clone_newpid`, `clone_newipc`, `clone_newuts` (`:180-185`); UID-mapped to 1000 (`:188`); rootfs is read-only bind mounts of `/usr`, `/lib`, `/bin`, `/etc` from `ALLAMA__SANDBOX_ROOTFS_PATH` (`:191-196`, image built from `docker/sandbox/Dockerfile`). Network is dropped in execute phase by default (`:171`) but re-enabled during package install. The container needs `SYS_ADMIN` + unconfined seccomp (`docker-compose.yml:139-142`). Resource limits are enforced via nsjail rlimits: `rlimit_as` (memory), `rlimit_cpu`, `rlimit_fsize`, `rlimit_nofile`, `rlimit_nproc`, `time_limit` (`executor.py:269-279`). All inputs to the protobuf config are validated against character allowlists (`_validate_path` `:82`, `_validate_env_key` `:66`, `_validate_cache_key` `:102`) to block injection. Execution returns through a `result.json` file in the bind-mounted `/work` (`:410-422`).
- **Action sandbox (untrusted mode):** `NsjailExecutor.execute_action()` (`:710`) mounts the registry package tarballs read-only at `/packages/0`, `/packages/1`, ... (`:649-654`), copies a `minimal_runner.py` into `/work` (`:680`), and crucially **does not** mount the `allama` app dir or DB credentials (`:656-657`). Secrets are pre-resolved by the trusted orchestrator and passed via env vars validated through `_validate_env_key`.
- **Fallback when nsjail isn't available:** `allama/sandbox/safe_executor.py:1-200`. This is an AST visitor (`ScriptValidator` `:175`) that enforces a deny-by-default import allowlist (`SAFE_STDLIB_MODULES` `:42-103`), blocks network modules (`NETWORK_MODULES` `:106-128`), blocks system modules (`SYSTEM_ACCESS_MODULES` `:131-165`), and bans `exec`/`eval`/`compile`/`__import__` (`:172`). Activated when `ALLAMA__DISABLE_NSJAIL=true`.
- **Agent runtime sandbox:** `allama/agent/sandbox/nsjail.py` reuses the same nsjail spawn pattern for the Claude/PydanticAI runtime. The orchestrator passes config, environment, and JWT tokens over a stdio bridge defined by the Pydantic protocol in `allama/agent/common/protocol.py` ("contract between the trusted orchestrator (outside NSJail) and the sandboxed runtime").

## 80+ integrations — what the number actually counts

Two integration patterns coexist:

1. **Python SDK adapters** in `packages/allama-registry/allama_registry/integrations/` — 20 modules, one per service (Splunk, CrowdStrike via FalconPy, ServiceNow, Slack SDK, Panther, AWS boto3, Microsoft Entra, LDAP3, MongoDB, etc.). Tools self-register through the `@registry.register(...)` decorator with `namespace`, `display_group`, and a `RegistrySecret` declaration. Secrets are fetched from a thread-local context that the untrusted runner populates *inside* the sandbox via `registry_secrets.set_context(flattened_secrets)` (`allama/executor/untrusted_runner.py:130`), then masked from stdout by `apply_masks_object` (`:115-117`).

2. **YAML "template tools"** in `packages/allama-registry/allama_registry/templates/tools/` — 349 `.yml` files across 49 vendor directories (CrowdStrike, Microsoft Sentinel, Splunk, Jira, ServiceNow, Okta, VirusTotal, AbuseIPDB, Datadog, PagerDuty, Wazuh, Elastic, etc.). Each YAML defines a mini sub-workflow that composes other registered actions.

So the "80+ integrations" claim is real once you count templates, but only ~20 are first-class Python adapters; the rest are YAML compositions over a generic HTTP/SDK base.

## Database / migrations

Alembic 1.13 with the `alembic-postgresql-enum` plugin (`pyproject.toml:27-28`); script location declared in `alembic.ini:6`. The `alembic/versions/` directory contains **121 migrations** as of the snapshot.

Multi-tenancy is layered via mixin classes (`allama/db/models.py:218-263`):

- `OrganizationModel` adds `organization_id: OrganizationID` (`:230`).
- `WorkspaceModel` extends `OrganizationModel` and adds `workspace_id: WorkspaceID` (`:251`).
- `PlatformModel` is for cross-org platform records (`:237`).
- `RecordModel` (`:140`) is the base for ownership-mixed records, with `owner_id: OwnerID` (`:341`) on `Ownership`.

Tenant isolation is enforced at the service layer, not at the DB level — every query in `allama/*/service.py` filters by `workspace_id` derived from the request `Role` (`allama/auth/types.py`). There is no row-level security.

## Frontend architecture

Next.js 15.5 (App Router) with React 18 (`frontend/package.json:100-109`). Styling via TailwindCSS + Radix UI primitives. State/data via TanStack Query 5; HTTP client auto-generated from the FastAPI OpenAPI spec by `@hey-api/openapi-ts` (`frontend/package.json:21-22, 131`). Editors use CodeMirror 6 with `lang-python`, `lang-yaml`, `lang-json`.

The **visual workflow builder** is `@xyflow/react 12.8` (React Flow) (`frontend/package.json:84`). The canvas component is `frontend/src/components/builder/canvas/canvas.tsx`. Auto-layout uses `@dagrejs/dagre 1.1`. The three node types are local components: `actionNode`, `selectorNode`, `triggerNode`, each with a separate `.tsx`.

## What is genuinely novel at the code level

1. **Temporal-as-control-plane for a SOAR DSL.** Most OSS SOARs (Shuffle, etc.) hand-roll a workflow engine on Celery, asyncio, or a state machine in PG. Allama gives every workflow run Temporal's full durable-execution guarantees (replay, signals, child workflows, schedules) and offloads result externalization to S3 to dodge Temporal's payload limits.
2. **Process-isolated PydanticAI tools with a per-tenant LiteLLM gateway.** Each `pydantic-ai` tool call is shelled out to a fresh subprocess (`allama/agent/tools.py:75-86`), and LLM calls are gated through a custom `CustomLogger` proxy (`allama/agent/gateway.py`) that does workspace-scoped credential resolution.
3. **Two-tier code sandboxing with explicit deny-by-default fallback.** The nsjail tier (`allama/sandbox/executor.py:117`) is paired with a strict AST allowlist (`allama/sandbox/safe_executor.py:42-172`) — most OSS SOARs simply trust their workers. The framing of "agent sandbox vs action sandbox vs untrusted-mode action sandbox" with distinct mount sets (`executor.py:561-684`) is a non-trivial engineering investment.

The stratsession brief's claim of a "WebAssembly Python sandbox" is **incorrect** — Allama uses nsjail (Linux user/mount/net/pid namespaces) with `cap_add: SYS_ADMIN`, not WASM/Pyodide/RustPython. The "80+ integrations" claim resolves to ~20 first-class Python adapters plus 349 YAML "template tool" files composed across 49 vendor directories.
