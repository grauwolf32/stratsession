# akto — code-level analysis

## 1. Architecture overview

Akto is a multi-service Java 8 / Maven monorepo built around **MongoDB + Kafka**. The dashboard webapp is Java 8 servlet + **Apache Struts 2** (regex action mapping), packaged as a WAR and served by the embedded **Jetty 9.4** plugin (`pom.xml:81`, `apps/dashboard/web/WEB-INF/web.xml`). Web is *not* Spring or Spark — it is the older Struts/Jetty stack, with action classes routed via `apps/dashboard/src/main/resources/struts.xml` and 13+ servlet filters (auth, RBAC, rate limit, mongo health, security headers — `web.xml:19-171`). Listener `com.akto.listener.InitializerListener` runs all bootstrap and cron work (`web.xml:174`). The frontend is a separate React 18 SPA bundled with webpack 5; legacy JSPs remain only for `login.jsp`, `verify_email.jsp`, `error.jsp` (`apps/dashboard/web/pages/*.jsp`). MongoDB is a single `mongo:6.0.1` container (`docker-compose.yml:6-11`); Kafka is the inter-service bus.

## 2. Module / package layout

Top level (`pom.xml:24-27`) is `apps/` + `libs/`. The `apps/` directory has **22 services** — atypically wide. The Java JVM ones share `com.akto.*` packages from `libs/dao` (MongoDB DAOs/DTOs) and `libs/utils`:

```
apps/dashboard           – Struts2 web UI + REST API (the monolith)
apps/api-runtime         – Kafka -> Mongo: traffic → API catalog
apps/mini-runtime        – Hybrid on-host runtime (com.akto.hybrid_runtime.*)
apps/api-analyser        – Separate consumer for PII/data-type analysis
apps/testing             – DAST test executor (com.akto.testing.*)
apps/testing-cli         – Standalone test runner
apps/threat-detection    – Real-time Kafka WAF/IDS (Java)
apps/threat-detection-backend – Service that ingests alerts
apps/data-ingestion-service – Struts HTTP intake of agent payloads
apps/database-abstractor – Shared DB facade microservice
apps/akto-gateway        – LLM-proxy gateway with guardrails dispatch
apps/agent-guard         – Go + Python policy services
apps/agent-traffic-analyzer – FastAPI / sentence-transformers
apps/agentic-guardrails  – 5 Python FastAPI ML services + router
apps/guardrails-service  – Cloudflare Worker (TS) + Go container
apps/mcp-endpoint-shield – CLI/IDE hook scripts (Python/JS/Lua) for
                           Claude, Cursor, Codex, Copilot, Gemini, Codex,
                           opencode, langchain, vertex-adk, etc.
apps/source-code-analyser, apps/billing, apps/account-job-executor,
apps/internal, apps/account-job-executor
```

The polyglot fan-out (Java + Go + Python + TypeScript + Lua) reflects a recent push into AI/agent territory layered onto a Java core.

## 3. Traffic ingestion

This is the heart of the system and the most heterogeneous subsystem. The canonical wire format is a JSON map serialized to a Kafka topic (default `akto.api.logs`), consumed by `apps/api-runtime/src/main/java/com/akto/runtime/Main.java:218`:

```java
main.consumer.subscribe(Arrays.asList(topicName, "har_"+topicName));
```

Records are decoded by `HttpCallParser.parseKafkaMessage` (`apps/api-runtime/.../parsers/HttpCallParser.java:1-80`) into `HttpResponseParams` DTOs, grouped per `accountId`, then handed to `handleResponseParams` (`runtime/Main.java:275`). There is **no eBPF code in this repo** — kernel mirroring is handled by an external "akto-mirroring" stack referenced only via CloudFormation/Lambda constants (`apps/dashboard/src/main/java/com/akto/utils/platform/MirroringStackDetails.java:5-23`: `CREATE_MIRROR_SESSION_LAMBDA`, `TRAFFIC_MIRROR_TARGET`, `LB_TRAFFIC_MIRROR_FILTER`, `AKTO_NLB`). Mirrored traffic is keyed by **AWS VXLAN id** which the runtime maps to an `ApiCollection` (`runtime/Main.java:48-79`).

Other ingestion paths converge on the same Kafka topic:

- **HTTP batch intake**: `apps/data-ingestion-service/src/main/java/com/akto/action/IngestionAction.java:49` accepts `List<IngestDataBatch>` from agents and pushes via `KafkaUtils.insertData`. (This file also contains a **hardcoded JWT bearer literal on line 52** — likely a development artifact that shipped to OSS; worth flagging.)
- **Burp / Postman / OpenAPI / HAR uploads** go through Struts actions: `BurpAction` (referenced in `web.xml`), `PostmanAction.java`, `OpenApiAction.java`, and `libs/utils/.../akto/har/HAR.java:14-37`. HAR entries are converted to the same JSON shape with `akto_vxlan_id` injected before being pushed to the runtime.
- **Syslog** TCP listener: `apps/data-ingestion-service/.../listener/SyslogTcpListener.java`.
- **MCP / AI agent hooks** (see §9) push `/mcp` envelopes through the same Struts endpoint.

## 4. API inventory + endpoint canonicalization

Canonicalization is in `apps/api-runtime/src/main/java/com/akto/runtime/APICatalogSync.java`. The clustering algorithm is `tryMergeUrls(URLStatic, URLStatic, boolean)` (`APICatalogSync.java:821-885`). Two same-length, same-method URLs are merged token-by-token; each differing token is classified to a `SuperType` via:

```java
if (NumberUtils.isParsable(...))         INTEGER
else if (ObjectId.isValid(...))          OBJECT_ID
else if (pattern.matcher(...).matches()) STRING   // UUID
else if (isAlphanumericString(...))      STRING
else if (mergeUrlsOnVersions && isValidVersionToken) VERSIONED
else                                     STRING (with templatizedStrTokens++)
```

Dictionary words are excluded (`DictionaryFilter.isEnglishWord`, line 844) so `/api/users` does not get over-templatized. URLs with more than one "free-form string" position are rejected (`templatizedStrTokens <= 1`, line 880). GraphQL URLs are exempt (line 837). MCP method names (e.g. `tools/call`) are filtered out post-merge (`APICatalogSync.java:897`). A Guava `BloomFilter<CharSequence>` of size 1M / FPP 0.001 (`APICatalogSync.java:76`) is used to suppress already-known endpoints. Parameter typing is done in parallel by `SingleTypeInfo` (collection `single_type_info`, see §7) which stores a per-(url, method, response_code, param) frequency record used both for inventory and PII inference.

## 5. Test template system

Tests are **YAML** documents, not Java classes. The shipped library ships as a JAR resource: `/tests-library-master.zip` (`apps/dashboard/src/main/resources/tests-library-master.zip`, loaded by `InitializerListener.loadTemplateFilesFromDirectory` `apps/dashboard/src/main/java/com/akto/listener/InitializerListener.java:2026-2050`). The zip is parsed in `InitializerListener.java:4380-4445`: each YAML is parsed by `TestConfigYamlParser`, then upserted into the `yaml_templates` Mongo collection (`libs/dao/.../test_editor/YamlTemplateDao.java`). Akto-authored templates are overwritten on every boot; user-authored ones use `setOnInsert` to preserve edits (lines 4400-4423). 131 hot-path templates also ship unzipped at `apps/dashboard/src/main/resources/inbuilt_test_yaml_files/` and 55 LLM-specific tests at `inbuilt_llm_test_yaml_files/`; the "1000+" figure comes from the bundled zip.

Example shape (`inbuilt_test_yaml_files/NoAuth.yaml`): `id`, `info{name, category, severity, cwe, cve}`, `api_selection_filters`, `execute{type, requests[{req:[ops]}]}`, `validate{response_code, …}`. Operators inside `req` (e.g. `remove_auth_header: true`, `modify_header`, `add_query_param`) are resolved by `apps/testing/src/main/java/com/akto/test_editor/execution/Executor.java` via `ExecutorAlgorithm` (line ~195) which iterates the `ExecutorNode` tree built from the YAML.

Per-test pipeline: `SecurityTestTemplate` (abstract, `apps/testing/.../yaml_tests/SecurityTestTemplate.java:22-77`) defines `filter()`, `requireConfig()`, `checkAuthBeforeExecution()`, `executor()`, `triggerMetaInstructions()`. Concrete subclass `YamlTestTemplate` (`apps/testing/.../yaml_tests/YamlTestTemplate.java:25`) wires the YAML's `filterNode`/`validatorNode`/`executorNode` through these phases.

A pluggable test family `NucleiExecutor.java` (same package) lets ProjectDiscovery Nuclei templates piggyback on the same framework. A second source of tests is `TestSourceConfig` (Mongo `test_source_configs`) — used for non-Akto authored / agentic fuzzing templates (`apps/dashboard/.../AgenticDashboardAction.java:714`).

## 6. DAST runner

The DAST worker is `apps/testing/src/main/java/com/akto/testing/Main.java`. It long-polls `testing_run` (`libs/dao/.../testing/TestingRunDao.java`) using a `findOneAndUpdate(SCHEDULED → RUNNING)` lease pattern. For each scheduled run, `TestExecutor` (`apps/testing/.../TestExecutor.java`) is invoked. The execution model is **Kafka-fanout when enabled**: `Producer.pushMessagesToKafka` (`apps/testing/.../kafka_utils/Producer.java:34-53`) sends one `SingleTestPayload` per (api × subcategory) to `TEST_RESULTS_TOPIC_NAME`; `ConsumerUtil` workers pick them up and run `YamlTestTemplate.run`. A back-pressure throttle (`throttleNumber > 1000` → sleep, lines 38-41) caps concurrent in-flight tests. When `IS_NEW_TESTING_ENABLED` is false (`Constants.IS_NEW_TESTING_ENABLED`, line 33) it falls back to in-process execution.

Findings are written to `testing_run_result` (most recent, deduped per template+endpoint), `vulnerable_testing_run_result` (positive only), and `testing_run_issues` (aggregated, surfaced in the issues page). Dedupe key is `(test_template_id, api_collection_id, url, method)` — issues use `MongoDBEnums.Collection.TESTING_RUN_ISSUES` (`libs/dao/.../testing_run_findings/TestingRunIssuesDao.java`).

## 7. MongoDB schema

DAOs live under `libs/dao/src/main/java/com/akto/dao/`. Each DAO extends `AccountsContextDaoWithRbac<T>` and returns its collection name from `getCollName()`. The Mongo *database name* is the numeric `accountId` (`SingleTypeInfoDao.java:47,55`) — **strict tenant isolation by physical DB**.

Key collections (one DAO per row):

| Collection | DAO / line | Purpose |
|---|---|---|
| `single_type_info` | `SingleTypeInfoDao.java:36` | Per-param type & frequency (inventory + PII) |
| `api_collections` | `ApiCollectionsDao.java` | API groups (one per VXLAN/host) |
| `api_info` | `ApiInfoDao.java` | Endpoint-level metadata |
| `sample_data` | `SampleDataDao.java` | Captured req/resp samples per endpoint |
| `traffic_info` | `TrafficInfoDao.java` | Per-endpoint counters |
| `yaml_templates` | `test_editor/YamlTemplateDao.java` | Test templates |
| `testing_run` / `testing_run_result` / `testing_run_result_summaries` | `testing/*Dao.java` | Test scheduling + results |
| `testing_run_issues` | `testing_run_findings/TestingRunIssuesDao.java` | Deduped findings |
| `users` | `UsersDao.java` | Auth identities |
| `account_settings`, `backward_compatibility`, `dashboard_logs`, `runtime_logs` | various | Infra |
| `mcp_allowlist`, `mcp_audit_info`, `mcp_recon_request`, `mcp_registry_config` | `McpAllowlistDao` etc. | MCP guardrails state |
| `guardrail_policies`, `markov` | `GuardrailPoliciesDao`, `MarkovDao` | Anomaly baselines |

Sub-areas (`libs/dao/.../dao/`): `testing/`, `threat_detection/`, `prompt_hardening/`, `agents/`, `agentic_sessions/`, `pii/`, `audit_logs/`, `billing/`, `loaders/`, `api_protection_parse_layer/` — ~40 top-level DAOs plus 15 sub-packages.

## 8. Frontend

`apps/dashboard/web/polaris_web/` is a separate npm project. React 18 + React Router 6 + Zustand, with **Shopify Polaris 11** as the design system (`apps/dashboard/web/polaris_web/package.json:14`). Charts via Highcharts, code editing via `monaco-editor`, Swagger rendering via `swagger-ui-react`, flow diagrams via `react-flow-renderer`. Built by webpack 5 (entry `apps/dashboard/web/polaris_web/web/src/apps/main/index.js`, `webpack.config.js:19`); the production bundle is uploaded to `d1hvi6xs55woen.cloudfront.net/polaris_web/$VERSION/dist/` (line 25). At runtime the Jetty webapp serves the bundle from `/polaris_web/web/dist/`. Pages live at `apps/dashboard/web/polaris_web/web/src/apps/dashboard/pages/` — `testing/`, `observe/`, `threat_detection/`, `agentic/`, `agent_team/`, `mcp-security/`, `guardrails/`, `nhi_governance/`, `prompt_hardening/`, `test_editor/`, `issues/`, etc.

## 9. MCP / AI agent guardrails

The MCP/agent posture is the most recent and largest addition. Three concentric layers:

1. **Client-side hooks** (`apps/mcp-endpoint-shield/`): 15 sub-directories of Python/Shell/Lua/JS hook scripts for Claude CLI, Claude Agent SDK, Cursor, Codex, Copilot, Gemini, GitHub CLI, opencode, neovim, langchain, vertex-ai-adk, litellm. Each implements the same protocol — `akto-validate-mcp-request.py`, `akto-validate-mcp-response.py`, `akto-validate-prompt.py` (`apps/mcp-endpoint-shield/claude-cli-hooks/akto-validate-mcp-request.py:36-60`). They POST tool calls to `AKTO_DATA_INGESTION_URL/mcp` and gate execution on the response. `MODE=atlas` rewrites the upstream `CLAUDE_API_URL` to `https://{device_id}.ai-agent.{connector}` (line 56) — a per-device routing trick that lets Akto sit transparently in front of Anthropic's API.

2. **akto-gateway** (`apps/akto-gateway/.../Gateway.java:30`, `LiteLLMAdapter.java`, `StandardGuardrailsAdapter.java`, `AdapterFactory.java`) — Java in-process proxy that calls `GuardrailsClient` before forwarding requests upstream and after receiving responses. Pluggable `GuardrailsAdapter` interface lets the gateway route to either Akto's own guardrails or LiteLLM's.

3. **Backend guardrails fleet**:
   - `apps/guardrails-service/` — Go container behind a Cloudflare Worker (`worker/src/index.ts:1-35`), with `pkg/validator`, `pkg/mediaprovider/{ocr,transcriber,azure_vision,azure_speech}`, file scanning, and a Kafka mode (`container/src/main.go:43`).
   - `apps/agentic-guardrails/` — five FastAPI/ONNX/`llm_guard` services (`prompt-injection`, `ban-words-content`, `intent-analysis`, `output-quality`, `toxic-speech`), front-ended by `model-router/router_service.py` which dispatches by `scanner_type` (`router_service.py:26`).
   - `apps/agent-traffic-analyzer/` — FastAPI + SentenceTransformer embeddings + `RAGStore`/`PatternLearner` to detect "base prompts with placeholders" (template fingerprinting for prompt injection / data exfil patterns, `src/api/agent_traffic_analyzer.py:40-58`).
   - `apps/threat-detection/` — Java Kafka consumer applying YAML threat filters and a parallel **Intel Hyperscan** regex engine (`apps/threat-detection/.../hyperscan/HyperscanThreatMatcher.java:26-40`) with location-aware pattern format `prefix::locations::regex_pattern`.

MCP storage on the dashboard side: `mcp_allowlist`, `mcp_registry_config`, `mcp_audit_info`, `mcp_recon_request` collections; CSV import of registries at `apps/dashboard/src/main/java/com/akto/action/McpAllowlistAction.java:51-90`. The MCP protocol vocabulary is centralized in `libs/utils/src/main/java/com/akto/mcp/McpSchema.java:23-40` (METHOD_TOOLS_CALL, METHOD_INITIALIZE, etc.) and is used by `APICatalogSync` to suppress MCP methods from API-clustering output.

## 10. What's genuinely novel at the code level

(a) The **endpoint canonicalization** in `APICatalogSync.tryMergeUrls` is more disciplined than most OSS API-discovery tools: dictionary-word exemption plus a `templatizedStrTokens <= 1` cap give noticeably better cluster quality than naive UUID/integer detection. (b) The **VXLAN-id-keyed multi-tenant mirroring pipeline** that maps AWS VPC traffic-mirror sessions to MongoDB-per-account is unusual — `accountId` literally becomes the Mongo database name. (c) The **MCP shield** is the broadest open-source CLI-hook surface for AI coding agents I've seen — 15 client integrations all funneling into a single `/mcp` Struts endpoint with a uniform JSON-RPC validation contract, plus a working `atlas` mode that hijacks `CLAUDE_API_URL` per device.

Note for follow-up: `apps/data-ingestion-service/.../IngestionAction.java:52` contains a hardcoded JWT (`DATABASE_ABSTRACTOR_SERVICE_TOKEN` literal) committed in source — worth flagging as a hygiene observation.
