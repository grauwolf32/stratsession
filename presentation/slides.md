# Slides — 28-slide outline

Each slide block: **slide title** · *suggested visual* · talking points · source references · estimated time.

> **Format conventions** — content is markdown bullets. Bold = on-slide; italic = speaker note only. Each slide has a **REF:** line pointing at the supporting file/section for fact-checking and live-Q&A backup.

---

## Movement 1 — Why now (slides 1-5)

### Slide 1 · Title
- **Perimeter Security: New OSS Tools & Approaches (2025-2026)**
- Subtitle: *What changed, what's worth adopting, what to test first*
- Date + speaker
- *Speaker note*: 30s — set scope: perimeter = anything internet-facing; OSS only; recent (2024-2026 entrants or major rewrites).
- **REF**: [`README.md`](./README.md)

### Slide 2 · Agenda
- Why now (5 slides)
- 5 clusters of recent OSS tooling (17 slides) — *with live demo opportunities*
- How to deploy (6 slides)
- **REF**: [`README.md`](./README.md)

### Slide 3 · The 2024-2026 inflection
- **Four forces converged**:
  - API explosion → API security category lagged behind web AppSec until 2026
  - Agentic AI introduced new perimeter (MCP servers, AI agents) → new attack surface
  - AI helps both sides → AI-driven vuln research is now operational, not research
  - OSS supply chain weaponized → tool selection now requires hygiene
- *Visual*: 2x2 grid: "more surface" × "more capable attackers"
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Recent advancements"; [`../blogs/cloud-native.md`](../blogs/cloud-native.md) on agentic AI; [`../blogs/oss-usage-case-studies.md`](../blogs/oss-usage-case-studies.md) Trivy incident.

### Slide 4 · OSS vs commercial: the gap closed
- **2022**: commercial AppSec platforms offered ~3x the coverage of OSS
- **2026**: OSS covers ~70% of commercial ASPM for teams ≤50 devs at $0 license cost
- **The remaining 30%**: centralized policy / compliance reporting / RASP / IAST — not tooling itself
- *Visual*: stacked bar chart, 2022 vs 2026, OSS coverage
- **REF**: [`../blogs/oss-usage-case-studies.md`](../blogs/oss-usage-case-studies.md) §"OSS-vs-commercial decision frameworks".

### Slide 5 · What "perimeter" means in 2026
- Internet-facing services + APIs + agentic-AI surfaces
- **Not** internal AppSec (that's covered in [`../sources/appsec/`](../sources/appsec/))
- **In scope today**: DAST, templated scanning, API discovery + testing, recon/ASM, WAF testing/defense, AI-assisted perimeter scanning
- **Out of scope today**: SAST, SCA at the SDLC layer, identity/AD
- *Visual*: concentric rings — perimeter as the outermost layer
- **REF**: [`../sources/perimeter/README.md`](../sources/perimeter/README.md)

---

## Movement 2 — What's new (slides 6-22)

### Slide 6 · Cluster 1 — Modern recon stack
- **5 tools, all Go, ProjectDiscovery suite**:
  - `subfinder` — passive subdomain enum
  - `httpx` — alive-host + tech fingerprint
  - `naabu` — port scan (Nmap alternative)
  - `katana` — modern crawler (Vespasian uses it)
  - `uncover` — *NEW*: Shodan/Censys/Fofa/Quake/Hunter as a unified CLI
- *Visual*: pipe-flow diagram showing the chain
- *Speaker note*: 90s — call out `uncover` as the genuinely-new addition; chained-tools-as-CLIs is the ProjectDiscovery pattern
- **REF**: [`../sources/perimeter/README.md`](../sources/perimeter/README.md); test scenario [`test-scenarios/01-recon-chain.md`](./test-scenarios/01-recon-chain.md)

### Slide 7 · Demo opportunity — Recon chain
- *Visual*: terminal recording / live
- Live demo (3 min): `subfinder -d <target> | httpx -tech-detect | naabu | katana` — one-line external attack surface map
- **LIVE DEMO CANDIDATE**
- **REF**: [`test-scenarios/01-recon-chain.md`](./test-scenarios/01-recon-chain.md)

### Slide 8 · Cluster 2 — Templated + AI-driven scanning
- **Nuclei v3.8.0 (April 2026)** — 12K+ community templates
- **New in 2026**:
  - `nuclei -ai "find admin pages with default creds"` — natural language → YAML template
  - `nuclei-ai-extension` — browser ext for live template generation
  - `nuclei-templates-ai` — AI-generated templates for CVEs without community coverage
  - XSS reflection-context analyzer (HTML / attribute / JS distinction)
  - Honeypot detector (deprioritizes honeypot-shaped targets)
- *Visual*: screenshot of AI extension generating a template from text
- **REF**: [`../reports/scanners.md`](../reports/scanners.md) §"Recent advancements"; test scenario [`test-scenarios/02-templated-scanning.md`](./test-scenarios/02-templated-scanning.md)

### Slide 9 · Cluster 3 — Modern DAST: Caido
- **First credible OSS Burp alternative in 5+ years**
- Rust + modern UX + active development since 2024
- Why it matters: Burp Suite is the unstated daily-driver for web pentesters; alternatives have been inferior for a decade
- *Visual*: side-by-side screenshot Burp vs Caido
- *Speaker note*: 90s — Caido isn't a Burp clone, it's a re-think with modern Rust performance. The community is forming
- **REF**: [`../sources/perimeter/README.md`](../sources/perimeter/README.md); test scenario [`test-scenarios/03-modern-dast.md`](./test-scenarios/03-modern-dast.md)

### Slide 10 · Cluster 4a — API discovery → spec (Vespasian)
- **The "spec from traffic" pattern** — observe wire traffic, generate OpenAPI 3.0 / GraphQL SDL / WSDL
- Two-stage: capture (browser/import) → generate (classify + probe + emit)
- Built on Katana for SPA crawling
- *Visual*: flowchart from [`../reports/api-security.md`](../reports/api-security.md)
- *Speaker note*: 60s — solves the "we have no API spec" problem that blocks every API-security engagement
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Vespasian"; test scenario [`test-scenarios/04-api-discovery-authz.md`](./test-scenarios/04-api-discovery-authz.md)

### Slide 11 · Cluster 4b — API authZ testing (Hadrian)
- **The killer feature**: three-phase mutation testing (setup → attack → verify) eliminates 200-OK-but-silently-ignored false positives
- 30 templates across REST (8), GraphQL (13), gRPC (9)
- 6 GraphQL DoS templates: alias / batching / circular fragments / depth / directive overloading / field duplication
- LLM-assisted attack planner (`--planner`) — prioritize templates instead of brute-force
- *Visual*: the three-phase diagram (setup creates resource → attack tries to modify → verify checks)
- **LIVE DEMO CANDIDATE** (recommended) — 60s against crAPI
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Hadrian template coverage"; test scenario [`test-scenarios/04-api-discovery-authz.md`](./test-scenarios/04-api-discovery-authz.md)

### Slide 12 · Demo — Hadrian's mutation test against crAPI
- 60s live: `hadrian test rest --api spec.yaml --roles roles.yaml --auth auth.yaml --planner`
- Expected: 3 BOLA findings in <60 seconds (claimed by Praetorian and reproducible)
- *Visual*: terminal recording
- **LIVE DEMO CANDIDATE**
- **REF**: [`test-scenarios/04-api-discovery-authz.md`](./test-scenarios/04-api-discovery-authz.md)

### Slide 13 · Cluster 4c — API platform: Akto
- **MIT-licensed alternative to Hadrian**
- 1,000+ test templates, including OWASP API Top 10 + HackerOne Top 10
- April 2026 release pivot: adds **MCP Registry Governance** and **Guardrails for AI Coding Assistants**
- When to choose: heavy live traffic + no API spec; broad coverage > per-template depth
- *Visual*: feature-comparison table (Hadrian vs Akto)
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Akto"; test scenario [`test-scenarios/06-api-platform.md`](./test-scenarios/06-api-platform.md)

### Slide 14 · Cluster 4d — Property-based fuzzing: Schemathesis
- **v4.18.1 (April 2026)** — actively developed
- Generates thousands of inputs from OpenAPI/GraphQL schema; Hypothesis library underneath
- Catches input-validation bugs Hadrian/Vespasian don't target
- Stateful workflows (create → get → delete) + invariant checking
- *Visual*: bug-finding rate graph
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Schemathesis"; test scenario [`test-scenarios/05-api-fuzzing.md`](./test-scenarios/05-api-fuzzing.md)

### Slide 15 · Cluster 4e — Stateful fuzzing: RESTler
- **Microsoft Research** — first stateful REST API fuzzer
- **Producer-consumer dependency inference** from OpenAPI: auto-chains create→read→update→delete
- RAFT platform archived 2026; effort consolidated into RESTler core
- When to use: deep stateful exploration of CRUD APIs
- *Visual*: dependency graph generated from a spec
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"RESTler"; test scenario [`test-scenarios/05-api-fuzzing.md`](./test-scenarios/05-api-fuzzing.md)

### Slide 16 · Cluster 4f — Spec audit: Cherrybomb
- **Rust CLI** — audits the OpenAPI spec *itself* for design flaws *before* you make a single request
- Catches: weak security schemes, missing rate limits, ambiguous response codes, type-coercion risks
- Complements: Vespasian generates the spec → Cherrybomb audits the spec → Hadrian tests the live API
- *Visual*: example finding output
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Cherrybomb"; test scenario [`test-scenarios/07-spec-audit-waf-ai.md`](./test-scenarios/07-spec-audit-waf-ai.md)

### Slide 17 · API security stack — putting Cluster 4 together
- *Visual*: the full pipeline from [`../sources/perimeter/README.md`](../sources/perimeter/README.md)
- **5 tools, 1 chain**: Vespasian → Cherrybomb → Akto/Schemathesis/RESTler → Hadrian
- crAPI as universal training target
- **REF**: [`../sources/perimeter/README.md`](../sources/perimeter/README.md) §"How they compose"

### Slide 18 · Cluster 5 — AI-assisted vuln research at the perimeter
- **Buttercup CRS** (Trail of Bits) — AIxCC 2nd place, $3M, fully OSS
- **GitHub Security Lab Taskflow Agent** — YAML-driven agentic vuln triage; 80+ OSS flaws found in beta
- **Promptfoo / GARAK / PyRIT / DeepTeam** — LLM red-team converged stack
- Cost data: Buttercup ran at **$181/point** on AIxCC scoring (28 bugs / 20 CWEs / 90% accuracy)
- *Visual*: Buttercup architecture diagram (high-level)
- **REF**: [`../reports/ai-vuln-research.md`](../reports/ai-vuln-research.md); test scenario [`test-scenarios/07-spec-audit-waf-ai.md`](./test-scenarios/07-spec-audit-waf-ai.md) §"AI vuln research"

### Slide 19 · MCP wrappers — the integration pattern of 2026
- **Pattern**: wrap any structured-output CLI in an MCP server → instantly callable from Claude / Cursor / IDE
- Three independent precedents shown in this corpus:
  - **Trivy MCP** — scanner-side
  - **Seclab Taskflow Agent's CodeQL MCP** — analyzer-side
  - **Snyk Agent Scan** — agent-side
- *Visual*: MCP architecture (host → server → tool exposed)
- *Speaker note*: 60s — the "give me a CLI" pattern of 2010 is being replaced by "give me an MCP server" in 2026
- **REF**: [`../reports/scanners.md`](../reports/scanners.md) §"MCP wrappers"

### Slide 20 · WAF as defense, not just target
- **Coraza** (Go-native ModSecurity successor) — 100% CRS-compatible, Wasm-deployable
- **OWASP CRS** — paranoia levels, anomaly scoring, regex-assembly toolchain
- Combined deployment patterns: Caddy / Envoy-Wasm / HAProxy SPOE / libcoraza-for-nginx
- *Visual*: deployment topology diagram
- **REF**: [`../reports/waf.md`](../reports/waf.md); test scenario [`test-scenarios/07-spec-audit-waf-ai.md`](./test-scenarios/07-spec-audit-waf-ai.md) §"WAF"

### Slide 21 · Targets: crAPI, OWASP Juice Shop
- **OWASP crAPI** — vulnerable API for the entire OWASP API Top 10
- **OWASP Juice Shop** — vulnerable web app for general web pentest
- Both Docker-compose deployable in <5 minutes
- All test scenarios in this deck use one or both
- *Visual*: crAPI architecture screenshot
- **REF**: [`test-scenarios/00-environment-setup.md`](./test-scenarios/00-environment-setup.md)

### Slide 22 · Themes recap
- **Six themes the 17 slides covered**:
  1. Recon = Go-tool chain + search-engine integration
  2. Scanning = templated + AI template gen
  3. DAST = Caido replaces Burp for OSS users
  4. API security = 5-tool composable stack (was 0 tools in 2022)
  5. AI-driven vuln research = operational, $181/point demonstrated
  6. MCP = the integration substrate for agent-callable security tools
- *Visual*: themes-as-callouts arranged around a hub diagram
- **REF**: [`../reports/api-security.md`](../reports/api-security.md), [`../reports/scanners.md`](../reports/scanners.md)

---

## Movement 3 — How to deploy (slides 23-28)

### Slide 23 · Recommended OSS perimeter stack
- **The 5-engineer-week deployment** (tested):
  - Discovery: Vespasian + Uncover + Subfinder + Httpx + Naabu + Katana
  - Spec audit: Cherrybomb
  - AuthZ testing: Hadrian
  - Input fuzzing: Schemathesis
  - Stateful fuzzing: RESTler
  - Manual testing: Caido
  - Training: OWASP crAPI
  - Templated CVE scan: Nuclei + AI extensions
  - Defense: Coraza + CRS
- *Visual*: stack diagram with annotated layers
- **REF**: [`../reports/api-security.md`](../reports/api-security.md) §"Operational stack recommendation"

### Slide 24 · POC priority — top 5 to test first
- **★ Hadrian + Vespasian** — the strongest single addition to AppSec/perimeter tooling in 2026
- **★ Caido** — modern DAST, immediate productivity for any web pentest
- **★ Nuclei + AI extensions** — already proven; AI integration is the new lift
- **Schemathesis** — property-based API fuzzing is a missing layer in most programs
- **Akto** — if you have heavy live traffic and no spec, use this instead of Vespasian+Hadrian
- *Visual*: 5-card layout, ★ marked
- **REF**: [`../TOOLS.md`](../TOOLS.md) §"Quick POC shortlist"

### Slide 25 · Cost framework
- **<10 devs**: $0 license cost, self-host OSS stack
- **10-50 devs**: keep OSS, resist commercial sales pressure until OSS is tuned
- **50+ devs**: buy ASPM (DefectDojo Pro / commercial) for triage layer; keep OSS for scanning
- Real numbers: Snyk Team 100 devs ≈ $67-90K/yr; Checkmarx / Veracode $40-200K+; OSS-only startup costs ~$0-5K
- *Visual*: cost-by-org-size table
- **REF**: [`../blogs/oss-usage-case-studies.md`](../blogs/oss-usage-case-studies.md) §"OSS-vs-commercial decision frameworks"

### Slide 26 · Risks specific to OSS perimeter tooling
- **Supply chain**: pin GitHub Actions to commit SHAs, not version tags (Trivy 2026)
- **LLM cost**: AI features (Nuclei AI, Hadrian planner, Buttercup) carry per-scan costs — budget caps required
- **Skill gap**: OSS demands more tuning expertise than commercial; budget ~0.25 FTE per 100 devs
- **Tool churn**: 2026 tools may be 2027 archive (RAFT example)
- *Visual*: risk-vs-mitigation table
- **REF**: [`../blogs/oss-usage-case-studies.md`](../blogs/oss-usage-case-studies.md) §"Trivy supply chain"

### Slide 27 · Test environment + scenarios — already prepared
- Every tool above has a runnable test scenario in this repo
- **Environment setup** under 15 minutes (Docker Compose)
- Tool-by-tool: 8 scenario files, all locally-runnable
- Map: [`test-scenarios/README.md`](./test-scenarios/README.md)
- *Visual*: directory tree screenshot
- **REF**: [`test-scenarios/README.md`](./test-scenarios/README.md)

### Slide 28 · Where to go from here
- **For tooling decisions**: [`../TOOLS.md`](../TOOLS.md) with verified GitHub links
- **For deep dives**: [`../reports/`](../reports/) — per-class comparison reports
- **For ongoing signal**: [`../blogs/`](../blogs/) — 27 sources curated
- **For conferences**: [`../conferences/`](../conferences/) — recent talks + tool releases
- **For trying any tool**: this deck's [`test-scenarios/`](./test-scenarios/)
- Q&A
- *Visual*: repo-map diagram

---

# Q&A preparation

Likely questions and where to find answers:

| Question | Where to look |
|---|---|
| "How does Hadrian compare to Burp Active Scan?" | [`../reports/api-security.md`](../reports/api-security.md) §"How is Hadrian different from OWASP ZAP or Burp Suite?" |
| "What's the LLM cost of running Nuclei AI / Hadrian planner?" | [`../reports/api-security.md`](../reports/api-security.md) — answer: per-call cost, configurable. Hadrian's `requires_llm_triage: true` per-template flag controls. |
| "Should we wait for Akto's API-security branch or move to MCP focus?" | [`../reports/api-security.md`](../reports/api-security.md) §"Akto" — Akto's MIT API-security branch is stable but not new-feature-tracked. Mid-2026 pivot is firm. |
| "What replaces ZAP for OSS DAST?" | This deck slide 9 — Caido. Coverage gap with ZAP: less mature attack catalog. Use both during transition. |
| "How do we handle the Trivy-style supply-chain risk?" | [`../blogs/oss-usage-case-studies.md`](../blogs/oss-usage-case-studies.md) §"Trivy 2026 incident" — commit-SHA pinning + dependency cooldowns. |
| "Is Vespasian production-ready?" | [`../reports/api-security.md`](../reports/api-security.md) §"Vespasian repo activity" — yes, actively developed, but treat early-2026 (v1.x) as "production-quality but evolving." |
| "How does Buttercup compare to commercial CRSs?" | [`../reports/ai-vuln-research.md`](../reports/ai-vuln-research.md) — only OSS finalist-grade CRS as of 2026. No direct commercial competitor. |
| "Won't an LLM-driven scanner produce false positives?" | This deck slide 11 — Hadrian's three-phase verify step. Verify-phase eliminates 200-OK-silently-ignored class. |
| "What about runtime application protection (RASP)?" | This deck slide 4 — RASP is a remaining gap; commercial alternatives still dominate. OSS coverage gap. |
| "Why no ZAP / Amass / WAF-A-MoLE?" | [`../sources/perimeter/README.md`](../sources/perimeter/README.md) §"Recent-tools rationale" — focus is recent (2024-2026) tools; mature tools documented elsewhere in repo. |

# Cut order (if running long)

| Time pressure | Cuts in order |
|---|---|
| -5 min | Drop slide 19 (MCP wrappers) — covered briefly in 17 |
| -10 min | Also drop slide 15 (RESTler) — Schemathesis covers the API-fuzzing message |
| -15 min | Also drop slide 18 (AI vuln research) — keeps perimeter focus |
| -20 min | Also drop slide 16 (Cherrybomb spec audit) |
| -25 min | Hard floor — slide count drops to 23, message survives intact |

# Source-of-truth cross-references

Every claim in this deck must be backed by:

- A submodule under [`../sources/perimeter/`](../sources/perimeter/) (for tool existence)
- A section in [`../reports/`](../reports/) (for analysis)
- An external link (CHANGELOG, blog post, paper) (for date / version / feature claim)

Audit pass before delivery: walk through `slides.md` and verify every **REF:** line resolves. If not, cut or rephrase the slide.
