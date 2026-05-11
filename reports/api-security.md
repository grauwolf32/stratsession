# API security — Vespasian + Hadrian

Vespasian and Hadrian are explicitly designed as a **pipeline**, not as alternatives. Praetorian shipped them together as a coordinated 2026 release:

- **Vespasian** discovers API endpoints by observing real HTTP traffic, then generates OpenAPI / GraphQL SDL / WSDL specs.
- **Hadrian** consumes those specs and performs **OWASP API Top 10 authorization testing** against the live API.

Together: `discover → spec → test → findings → triage`. Both repos are pure Go, both released early 2026, both Apache 2.0. The two `CLAUDE.md` files describe interlocking architectures that read like halves of one tool.

| | Vespasian | Hadrian |
|---|---|---|
| Stage | Discovery + spec generation | Authorization testing |
| Inputs | Live URL (crawl) or Burp XML / HAR / mitmproxy capture | API spec (OpenAPI / GraphQL / proto) + roles.yaml + auth.yaml |
| Outputs | OpenAPI 3.0 YAML / GraphQL SDL / WSDL XML | Terminal / JSON / Markdown findings |
| Protocols | REST + GraphQL + SOAP | REST + GraphQL + gRPC |
| Repo size | 2.7 MB | 2.8 MB |
| LLM optional | No | Yes (planner + triage) |
| Auto-config | N/A | Claude Code skill `hadrian-openapi-authz` |

## What's novel in Vespasian

The orthodox API-discovery approach has two paths: **(a) crawl the host for `/swagger.json`, `/openapi.yaml`, `/.well-known/*`**, or **(b) static analysis of the codebase**. Both miss the API surface that's actually exercised at runtime by SPAs, mobile clients, and microservices.

Vespasian takes a third approach: **observe wire traffic, classify it, generate specs.**

1. **Two-stage pipeline by design.**
   ```
   Capture → capture.json → Generate
   ```
   The `capture.json` intermediate is JSON-inspectable. You capture once, generate many. You can debug capture bugs separately from generation bugs. Offline analysis is possible.
2. **Three capture sources, one format.**
   - **Headless browser crawler** (built on [Katana](https://github.com/projectdiscovery/katana)) — drives a real Chrome with JS execution. Captures everything the SPA actually calls.
   - **Burp Suite XML import**
   - **HAR 1.2 import**
   - **mitmproxy import**, including mitmproxy's native tnetstring `.mitm` format with **layered safety caps**: 500 MB per file, 64 MB per tnetstring element, 1 M entries per list/dict, 500 K flows per native stream. (The CLAUDE.md mentions this — Praetorian had to write a defense-in-depth parser because tnetstring is otherwise unbounded.)
3. **API-type auto-detection.** No need to tell Vespasian "this is GraphQL." Classifier infers from:
   - **REST**: JSON/XML content-type, `/api/`, `/v1/`, HTTP method, response structure
   - **GraphQL**: `/graphql` path (0.70), query syntax in POST body (0.85), `data`/`errors` keys (0.80), combined (0.95)
   - **WSDL**: SOAPAction header, SOAP envelope in body, `?wsdl` URL parameter
   Each signal has an explicit confidence score (0-1); tunable via `--confidence`.
4. **Three-tier GraphQL introspection.**
   - **Tier 1**: Full introspection with descriptions, deprecation, directives.
   - **Tier 2**: Minimal-complete query (no descriptions, deprecation, directives) — bypasses some WAF rules.
   - **Tier 3**: Smallest-possible query — last resort.
   - **Fallback**: Traffic-based inference from observed queries when introspection is disabled entirely.
   This staircase handles the increasingly common pattern of "introspection is disabled in production."
5. **Path normalization with context-aware preservation.** `/users/42` and `/users/87` collapse to `/users/{id}`, but `/me`, `/self` are recognized as literal endpoints and preserved. UUID detection. The CLAUDE.md mentions "context-aware parameter naming."
6. **SSRF protection by default.** Crawling and probing private/loopback addresses is **blocked by default**. The `--dangerous-allow-private` flag is required to scan localhost / RFC1918 / link-local targets. The CLAUDE.md notes "DNS rebinding mitigation" on the probe path. This is unusually defensive for a pentest tool.
7. **Active probing strategies are pluggable.** OPTIONS discovery, JSON schema inference from observed responses, WSDL document fetching, GraphQL introspection (the three-tier strategy). Each is a `ProbeStrategy` interface implementation in `pkg/probe/`. Add a new probe by implementing the interface.
8. **Built on Katana**, a [ProjectDiscovery](https://github.com/projectdiscovery/katana) tool. Reuses an existing strong crawler rather than reinventing.

The strategic novelty: **Vespasian is the first OSS tool that gives you an actual API specification, not just a list of URLs, from runtime traffic.** Most discovery tools dump URLs at you. Vespasian dumps an OpenAPI 3.0 spec — directly consumable by Burp Suite, Postman, ZAP, and (critically) by Hadrian.

## What's novel in Hadrian

Hadrian's framing: **"Most API security scanners test for injection and configuration issues but miss authorization logic bugs — the #1 and #5 most critical API vulnerabilities according to OWASP."** This is correct: ZAP and Burp Active Scan don't natively understand "user A's data" vs. "user B's data" — that requires *roles, permissions, and identities*.

Hadrian solves this with **role-based authorization testing**:

1. **Define your roles once.** `roles.yaml` lists roles (admin, user, guest), each with declared **permissions** in `<action>:<object>:<scope>` format (e.g., `read:user:own`, `write:order:org`, `*:*:all`). Actions: `read | write | delete | execute | *`. Scopes: `public | own | org | all | *`.
2. **Define auth methods once.** `auth.yaml` describes how to authenticate as each role (bearer token, basic auth, API key, cookie).
3. **Hadrian cross-tests every role combination automatically.** For every endpoint × every template × every role pair (attacker / victim), it runs the appropriate authorization test.
4. **Three-phase mutation testing** is the killer feature, and it's the most genuinely new technique in any of the 17 repos:
   ```
   Phase 1: SETUP   — Victim creates a resource (stores resource ID)
   Phase 2: ATTACK  — Attacker attempts to delete victim's resource
   Phase 3: VERIFY  — Confirm the resource was actually deleted
   ```
   This eliminates the false-positive class that has plagued authorization testing forever: APIs that return `200 OK` for forbidden requests but silently ignore them. Hadrian's verify phase actually checks the state change. The README's headline number — *"3 critical BOLAs in OWASP crAPI in under 60 seconds"* — is the proof point.
5. **Multi-phase setup via array syntax.** Setup phases can be a single phase (single object) or multiple sequential phases (array). The example in `CLAUDE.md`:
   ```yaml
   test_phases:
     setup:
       - path: "/api/user/dashboard"
         auth: "victim"
         store_response_fields:
           victim_id: "id"
           victim_video_id: "video_id"
       - path: "/api/user/dashboard"
         auth: "attacker"
         store_response_fields:
           attacker_video_id: "video_id"
     attack:
       path: "/api/resource/{victim_id}"
       auth: "attacker"
   ```
   This unlocks BOPLA (Broken Object Property Level Authorization) — testing whether attacker can mutate properties of victim's object — which requires juggling two simultaneous setup contexts.
6. **Template-driven** — 30 built-in YAML templates (8 REST / 13 GraphQL / 9 gRPC) cover the OWASP API Top 10. You can author custom templates for app-specific authorization rules. The grammar (endpoint_selector / role_selector / http / detection) is independently designed from but conceptually identical to Seclab Taskflow Agent's grammar.
7. **LLM-assisted attack planning** (`--planner`). Instead of brute-forcing every operation × template × role combination, an LLM analyzes the API spec and produces a **prioritized attack plan** of which endpoints to attack with which templates first. Combine with `--planner-only` to skip the brute-force fallback entirely. Providers: OpenAI / Anthropic / Ollama. This is unique in API testing today — Burp's AI features don't do template prioritization.
8. **LLM triage** (`--llm-provider`) — separate from the planner, this triages *findings* to reduce false positives. Ollama for local, OpenAI/Anthropic for higher quality.
9. **Claude Code skill** at `skills/hadrian-openapi-authz/` — *auto-generates `auth.yaml` and `roles.yaml`* from your API spec. Load Hadrian as a plugin (`claude --plugin-dir .`) and prompt "Generate Hadrian config from my OpenAPI spec." This eliminates the biggest setup-time blocker for authorization testing.
10. **Adaptive rate limiting.** `pkg/runner/ratelimit_client.go` — proactive limiting (5 req/s default) plus reactive backoff on 429/503 responses. Audit logging to `.hadrian/audit.log` for compliance.
11. **gRPC support is real, not bolted on.** 9 gRPC-specific templates. The proto file is the input; Hadrian generates messages, varies fields, and tests authZ across role pairs. This is unusual — gRPC support in commercial tools is patchy.

## The pipeline in practice

```
$ vespasian scan https://api.example.com -H "Authorization: Bearer $TOKEN" -o api.yaml
# → captures traffic, classifies as REST, generates OpenAPI 3.0
$ claude --plugin-dir hadrian -p "Generate Hadrian config from api.yaml"
# → produces auth.yaml + roles.yaml
$ hadrian test rest --api api.yaml --roles roles.yaml --auth auth.yaml --planner
# → runs LLM-planned attack first, then brute-force fallback
```

End-to-end automated API security assessment in three commands. This is a **substantially new capability**. The previous state of the art was:
- Run Burp Active Scan (no authZ awareness)
- Manually write Postman collections to test authZ
- Pay for an annual pentest

Hadrian + Vespasian + the Claude Code skill collapses that into something a CI pipeline can run.

## Limitations

- **Vespasian discovers only what the crawl exercises.** If your frontend never calls `/api/admin/dangerous`, Vespasian doesn't find it. Static analysis tools can find unexercised endpoints; Vespasian can't.
- **Hadrian's mutation tests modify data.** Always run against staging environments. The README is explicit about this.
- **gRPC support requires a `.proto` file.** Without one, you fall back to REST/GraphQL.
- **LLM costs.** The planner uses an LLM per scan; triage uses an LLM per finding. Costs aren't free, but per-scan cost is bounded.
- **Auth.yaml + roles.yaml are still the hardest part of setup.** The Claude Code skill helps, but you must understand your own application's role model. No tool can extract that from nothing.

## Strategic read

Vespasian + Hadrian is the **first OSS tool chain that actually competes with commercial API security platforms** like Salt Security, Noname, Traceable, 42Crunch. Three observations:

1. **Praetorian published this as "complete," not "experimental."** The 30-template OWASP API Top 10 coverage, multi-phase mutation testing, gRPC support, and LLM integration are all production-quality. The Claude Code skill is a deliberate signal — they want adoption.
2. **The MCP / agent integration story is more mature than for any other tool in this submodule set.** Hadrian was *designed for* agent integration from day one. Compare to Trivy MCP, which was retrofitted.
3. **Combined with Buttercup or Seclab Taskflow Agent**, you can imagine the full pipeline: agent runs Vespasian → generates spec → invokes Hadrian → triages findings via Taskflow Agent → opens GitHub issues automatically. None of the pieces are missing in 2026. The integration glue is what's still bespoke.

If you're an AppSec lead choosing where to invest **one** new tool POC this quarter, this is the strongest candidate in the 17.

---

# Recent advancements & broader landscape

## What landed in 2025–2026 across the OSS API-security ecosystem

The Vespasian + Hadrian release is the most consequential 2026 event in this category, but it is one of *several* materially new capabilities the OSS ecosystem shipped in the past 12 months. Tools listed below are *not* in `sources/appsec/` but are worth tracking for any team building an API-security program.

### Hadrian template coverage — verified from the submodule

The current Hadrian repo (HEAD `95edf37`, May 2026) ships **30 templates** across three protocols:

| Protocol | Templates (count) | OWASP API Top 10 coverage |
|---|---|---|
| **REST** (`templates/rest/`) | 8 | API1 BOLA read/write/delete, API2 broken auth, API3 excessive data exposure, API5 BFLA admin access, API8 misconfig, API9 inventory |
| **GraphQL** (`templates/graphql/`) | 13 | API1, API2, API3 (data exposure + injection), API4 (alias DoS, batching, circular fragments, depth, directive overloading, field duplication), API5 BFLA, API8 (errors + introspection) |
| **gRPC** (`templates/grpc/`) | 9 | API1 read/write/delete, API2, API3, API5, API8, deadline manipulation, metadata injection |

The GraphQL section is the strongest of the three — six dedicated API4 (Unrestricted Resource Consumption) templates including **alias DoS**, **batching**, **circular fragment**, **depth**, **directive overloading**, and **field duplication** attacks. These are GraphQL-specific abuse patterns that ZAP and Burp don't natively cover.

Per-template structure (verified from `02-api1-bola-write.yaml`):

```yaml
info:
  name: ...
  category: "API1:2023"
  severity: "CRITICAL"
  requires_llm_triage: true          # opt-in to LLM verification
  test_pattern: "simple"             # or "mutation" for three-phase tests

endpoint_selector:
  has_path_parameter: true
  requires_auth: true
  methods: ["PUT", "PATCH"]

role_selector:
  attacker_permission_level: "lower"
  victim_permission_level: "higher"

http: [...]
detection:
  success_indicators: [...]
  failure_indicators: [...]
  vulnerability_pattern: "attacker_modified_victim_resource"
```

The `requires_llm_triage: true` flag on per-template basis lets you reserve LLM calls only for findings that warrant deeper analysis — a cost-control mechanism missing from comparable commercial tools.

### Vespasian — repository activity in 2026

Recent commits (`a845921`, May 2026, HEAD) show active development in several directions:

- **CLAUDE.md drift detection in CI** (`297bac5`, `014cebd`) — Praetorian uses Anthropic's [`claude-md-drift`](https://github.com/anthropics/claude-md-drift) GitHub Action across all their public OSS to ensure CLAUDE.md docs stay accurate as the code evolves. Worth adopting if you maintain LLM-readable docs in any project.
- **mitmproxy import bug fixes** (`ec02178`) — the layered safety caps in tnetstring parsing got polished post-release.
- **SPA crawl URL resolution + XHR/fetch interception fixes** (`698dba2`) — addressing a long-standing class of misses in single-page-app crawls.
- **Titus secrets scanning, Gemini PR review, go-sec v2.1.0, codex-code v2.1.2** — heavy internal-tooling investment around CI security workflows. Worth a read for any Go-shop interested in modern CI security pipelines.

The repo is not in maintenance mode — it's a primary investment area for Praetorian.

## Adjacent OSS API-security tools worth knowing about

These are the most important *non-submodule* OSS tools in the API-security space as of mid-2026. Read with a "what is this good at that Vespasian / Hadrian isn't?" lens.

### Akto — https://github.com/akto-api-security/akto

The most direct OSS competitor to Hadrian. Akto is an **API discovery + testing platform** under MIT license. Differences vs. Hadrian:

- **Inventory-driven, not spec-driven.** Akto continuously monitors live traffic (eBPF / mirror / Burp ingestion / Kong ingress / Postman import) and builds an API inventory from observed requests, rather than starting from an OpenAPI/proto file.
- **1,000+ test templates** including OWASP API Top 10, HackerOne Top 10, BOLA / authentication / SSRF / XSS / security misconfigs. Significantly larger template library than Hadrian's 30, but more shallow per-template (less verification logic, no three-phase mutation testing).
- **CI/CD integrations** for embedding scans in pipelines.
- **MongoDB-backed multi-tenant deployment** — heavier infrastructure than Hadrian's single-binary Go CLI.

> Note: Akto's commercial focus has **pivoted to AI agent / MCP security** in 2025–2026 (April 2026 release adds *Guardrails for AI Coding Assistants* and *MCP Registry Governance*). The original OSS API-security codebase remains MIT and usable, but new features are landing on the agentic-security product. If you adopt Akto for API testing in 2026, expect to be on a stable but not-actively-extended OSS branch.

**When to use Akto over Hadrian**: you have heavy live traffic and no API spec, and want broad coverage > per-template depth.

### Schemathesis — https://github.com/schemathesis/schemathesis

Property-based API fuzzer for OpenAPI 3.x and GraphQL. Latest release **v4.17.0 (April 2026)**. Distinct philosophy from Hadrian:

- **Property-based testing via Hypothesis** — generates thousands of inputs from schema constraints, checking that responses don't violate schema or invariants. Finds edge-case input-validation bugs Hadrian and Vespasian don't target.
- **Mutation-based and negative testing modes** — generates inputs that intentionally violate schema constraints. Specifically targets "API claims input validation, but actually accepts invalid data."
- **Stateful testing** — chains requests (create → get → delete) and checks invariants across state transitions.
- **Captured-response-data reuse** in subsequent test phases (similar concept to Hadrian's `store_response_fields`).
- **`auth.dynamic.openapi.<scheme>` config block** for token-fetch auth without writing Python code (added in 2026).
- **`--request-retries` with exponential backoff** — handle flaky test targets.
- **Adopters**: Spotify, WordPress, JetBrains, Red Hat.

**When to use Schemathesis alongside Hadrian**: Schemathesis catches input-validation bugs (data-shape / boundary / encoding violations); Hadrian catches authorization bugs. Both are needed for serious API security testing.

### Microsoft RESTler — https://github.com/microsoft/restler-fuzzer

The first stateful REST API fuzzer, from Microsoft Research. Still actively maintained in 2025–2026 (`getProducer` improvements in May 2025, HTTP transport stability + logging in March 2025).

- **Producer-consumer dependency inference** — RESTler analyzes OpenAPI specs and figures out which endpoint produces resources consumed by which other endpoint, then chains them. Mostly automatic.
- **Stateful fuzzing** finds bugs in multi-step flows that single-request fuzzers (like Schemathesis's default mode) miss.
- A **2025 academic paper** extended RESTler with resource-level dependencies (beyond just producer-consumer) for more valid sequences.
- **RAFT (REST API Fuzz Testing) platform** was archived in 2026 — Microsoft is consolidating efforts into the core RESTler engine. Existing RAFT code is preserved but won't get new features.

**When to use RESTler over Hadrian**: deep stateful exploration of CRUD APIs where the sequence matters more than authZ specifically.

### Cherrybomb — https://github.com/blst-security/cherrybomb

Rust CLI for OpenAPI specification *auditing* + lightweight API security testing. Audits the spec itself for design flaws (e.g., security definitions, missing rate limits, weak auth schemes) before any request is made — complementary to Vespasian's "spec from traffic" direction.

### APICheck — https://github.com/BBVA/apicheck

BBVA's "DevSecOps toolset for REST APIs." Broader-scope DevSecOps lifecycle tool (replay, monitoring, security testing, fuzzing). Less polished than the Praetorian tools but has the broadest set of subtools.

### Burp Suite AI features (commercial)

**Burp AI** released in 2025 added:

- **Automated Issue Validation** — Burp Scanner's findings get re-validated by an LLM that builds proof-of-concept exploits. Reduces false positives.
- **Instant AI Insights** — Burp Repeater shows LLM-summarized explanations of HTTP headers, cookies, client-side JS. Speeds up manual review.
- **Montoya API for extensions** — extensions can send prompts to LLMs and embed AI features.
- **No-retention guarantee** — PortSwigger commits that user data is not retained or used for model training.

PortSwigger's positioning: Burp AI is augmentation of the manual workflow, not replacement. Worth knowing if your AppSec team uses Burp for manual API testing and wants AI-assisted triage.

### Snyk Agent Scan — https://github.com/snyk/agent-scan

Released February 2026, GA March 2026 as part of Snyk's **Agent Security** suite. Not a direct API-security tool — it's an **AI-agent and MCP-server security scanner**. Relevant because:

- Auto-discovers local agent configs (Claude, Cursor, Windsurf, Gemini CLI).
- Connects to MCP servers, fetches tool descriptions, scans for **15+ risks**: prompt injection, tool poisoning/shadowing, toxic flows, malware payloads, untrusted content, credential handling, hardcoded secrets.
- Runs in **scan mode** (one-shot CLI report) or **background mode** (periodic scans → Snyk Evo instance).

This is a hint at where API security overlaps with agent security: any API that an LLM agent calls becomes part of the agent attack surface. OWASP's emerging **MCP Top 10** and **Top 10 for Agentic Applications** projects are formalizing this overlap.

### crAPI — https://github.com/OWASP/crAPI

The reference training target for API security. Used by Hadrian's tutorial documentation (`test/crapi/` in the Hadrian repo). Docker-compose-deployable, demonstrates the full OWASP API Top 10. If you're learning, run Hadrian against crAPI as the first exercise.

## Major themes the OSS API-security ecosystem is solving in 2026

1. **Spec-from-traffic discovery is now standard.** Vespasian, Akto, and several commercial tools all do this. The mature pattern is two-stage (capture → generate), which Vespasian formalized.
2. **Authorization testing has moved from "afterthought" to "headline feature".** Pre-2025, most scanners ignored authZ. In 2026, Hadrian, Akto, Schemathesis stateful mode, and commercial Levo/StackHawk all explicitly test authZ — this is convergence.
3. **GraphQL gets dedicated abuse-pattern coverage.** Six API4 templates in Hadrian for GraphQL DoS alone is striking. The GraphQL attack surface (introspection, alias DoS, batch/circular/depth attacks, directive overloading) is now standard knowledge in API scanners.
4. **gRPC support is real.** Hadrian ships nine gRPC templates; commercial tools are starting to follow. The "we don't test gRPC" gap is closing.
5. **LLM triage + LLM planning are separating into two distinct features.** Hadrian models this cleanly: `--llm-provider` triages findings to reduce false positives; `--planner` chooses *what to test first* to reduce brute-force time. Other tools are still conflating them.
6. **WAF parsing-discrepancy attacks are now a category.** **WAFFLED** research (arxiv 2503.10846) demonstrated **1,207 bypasses across 5 well-known WAFs** by exploiting parsing differences between WAF and upstream app. This is the next attack class to bake into API security testing.
7. **OWASP API Security Top 10 update pending.** The 2023 list is still current in 2026; agentic AI's interaction with APIs is widely expected to drive a 2026 or 2027 update. Hadrian's API4 GraphQL DoS templates anticipate the direction.

## Operational stack recommendation (2026)

If you're building an OSS API-security capability today, the canonical stack is:

```
Discovery:         Vespasian          (traffic → OpenAPI/SDL/WSDL)
Spec audit:        Cherrybomb         (audit the spec itself)
AuthZ testing:     Hadrian            (cross-role authZ, three-phase mutation)
Input fuzzing:     Schemathesis       (property-based fuzzing from schema)
Stateful fuzzing:  RESTler            (producer-consumer chains)
Manual testing:    Burp Suite + Burp AI   (irreplaceable for tricky cases)
Training:          OWASP crAPI        (vulnerable target)
Agent security:    Snyk Agent Scan    (when APIs are agent-callable)
```

None of these duplicate each other materially. Together they cover the full OWASP API Security Top 10 with verification depth far exceeding what any single tool provides. **Hadrian + Vespasian is the strongest *new* contribution in this stack** — that's why they got dedicated coverage above — but they're meant to compose with the rest, not replace them.
