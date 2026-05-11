# 06 · API platform — Akto

**Slide reference**: 13 · **Estimated time**: 30-60 minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md)

## Goal

Deploy Akto, capture crAPI traffic, run its 1,000+ test templates against crAPI, and review the dashboard. Position as the **MIT-licensed alternative to Hadrian**: heavier infrastructure but broader test catalog and a dashboard for ongoing monitoring.

When to choose Akto over Hadrian: heavy live traffic + no API spec + want a dashboard. When to choose Hadrian: depth-of-verification (three-phase mutation testing) > breadth-of-coverage.

## Tool

| Tool | Submodule |
|---|---|
| **Akto** | [`../../sources/perimeter/akto`](../../sources/perimeter/akto) — pinned to `guardrails-service-1.90.4` |

## Scenario A — Deploy Akto (15-30 minutes)

Akto's footprint is the heaviest in this entire test set: requires **Docker Compose + MongoDB + multiple Java services**.

### Option 1 — Docker Compose (recommended for testing)

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/akto

# Check the canonical compose file (location varies by version)
find . -name "docker-compose*.yml" -path "*/deploy/*" | head -5

# Use the standalone version
cd deployment/local
docker compose up -d

# Wait for ~3 minutes (MongoDB init takes time)
docker compose ps
```

### Option 2 — k8s/Helm

For longer-running deployments:
```bash
helm repo add akto https://akto-api-security.github.io/helm-charts
helm install akto akto/akto --namespace akto --create-namespace
```

### Verify Akto is up

```bash
# Akto dashboard
curl -sf http://localhost:9091 > /dev/null && echo "OK"

# Login: open http://localhost:9091 in browser
# Default credentials: admin@akto.io / 1cce95d5-9c41-4d3e-95a3-3a5d59d22b3f
# (Check Akto docs for current default — they rotate)
```

## Scenario B — Capture crAPI traffic into Akto

Akto's value proposition is **inventory from live traffic, not from a spec**. Three ingestion paths:

### Path 1 — Mirror traffic via Burp/Caido extension

1. In Akto dashboard: **Settings → Connectors → Burp Suite** → download the Akto Burp extension
2. In Caido (or Burp): load the extension
3. Configure to forward to Akto's `:9091/api/ingest`
4. Browse crAPI normally — every request is captured

### Path 2 — eBPF-based mirroring (production pattern)

Akto's deepest integration: deploy an eBPF probe on the API host that mirrors traffic to Akto. For the lab:

```bash
# Akto provides a 'traffic-mirroring' agent
docker run -d --rm \
  --network stratlab \
  --cap-add NET_ADMIN \
  --pid host \
  -e AKTO_URL=http://akto-runtime:9090 \
  akto/traffic-mirroring-agent
```

Then traffic to `172.30.0.10:8888` (crAPI) is mirrored to Akto for inventory + testing.

### Path 3 — Postman collection / OpenAPI spec import

Easiest for a demo. In Akto dashboard:

1. **API Inventory → Add Collection → Upload OpenAPI**
2. Upload `/tmp/crapi-openapi.yaml` (from scenario 04)
3. Akto inventories all endpoints

## Scenario C — Run test templates

Akto ships with **1,000+ test templates** across OWASP API Top 10, HackerOne Top 10, and category-specific checks.

```
Categories visible in the dashboard:
- Broken Object Level Authorization (BOLA)
- Broken Authentication
- Excessive Data Exposure
- Lack of Resources & Rate Limiting
- Broken Function Level Authorization (BFLA)
- Mass Assignment
- Security Misconfiguration
- Injection (SQL, NoSQL, OS Command)
- Improper Asset Management
- Insufficient Logging & Monitoring
- Server Side Request Forgery
- + many JWT / OAuth / SSO-specific tests
```

### Run a test suite via dashboard

1. **Testing → New Test Run**
2. Select collection: "crAPI"
3. Select test categories: "OWASP API Top 10"
4. Configure authentication: paste `${VICTIM_TOKEN}` as bearer auth
5. **Run** — takes 5-15 minutes

### Run via CLI (CI/CD pattern)

```bash
docker run --rm \
  --network stratlab \
  -e AKTO_API_KEY=... \
  -e AKTO_DASHBOARD_URL=http://akto-dashboard:9091 \
  akto/akto-testing-cli \
  --collection crAPI \
  --tests owasp-api-top-10 \
  --output /tmp/akto-results.json
```

## Scenario D — April 2026 features: MCP Registry + AI Coding Guardrails

The submodule is pinned to `guardrails-service-1.90.4` — Akto's April 2026 pivot toward agentic security. Two new capabilities worth demoing:

### MCP Registry Governance

```bash
# Akto's MCP Registry: scans MCP servers exposed to agents
# Dashboard → MCP Registry → Add MCP Server
# URL: stdio:///path/to/your/mcp-server
```

This is the **same problem space** as Snyk's `agent-scan` — except Akto runs it as a continuous-monitoring service vs. one-shot CLI.

### Guardrails for AI Coding Assistants

```bash
# Dashboard → AI Guardrails → Connect Claude Code / Cursor
# Akto injects guardrails that scan agent tool-calls for malicious behavior
```

This positions Akto as an **AI-perimeter** product, not just API-perimeter. The April 2026 release indicates the company's commercial focus has pivoted; the OSS API-security branch remains stable.

## Scenario E — Compare Akto vs Hadrian results on the same target

After running both Hadrian (scenario 04) and Akto (this scenario) against crAPI, compare:

| Metric | Hadrian | Akto |
|---|---|---|
| Time to first finding | 30s | 5-10 min (includes deploy) |
| Total findings | ~10-20 | ~40-80 |
| False-positive rate | Low (three-phase verify) | Medium (broader, less verified) |
| Setup complexity | Low (CLI) | High (containers + DB + dashboard) |
| Ongoing monitoring | No | Yes |
| Template authoring | YAML, straightforward | YAML with Akto-specific DSL |
| Compliance reporting | None | Built-in (some compliance maps) |
| Best for | One-shot pentest, CI | Continuous API monitoring program |

**Headline data point for slide 13**: Akto's catalog is ~30× larger than Hadrian's (1000+ vs 30), but Hadrian's per-test depth (three-phase verify) is materially higher. They're complementary.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| MongoDB fails to start | Volume permission issue | `docker compose down -v && rm -rf data/` and retry |
| Dashboard shows "0 collections" | Spec/collection import failed | Check `docker logs akto-dashboard` |
| Tests stuck at "running" forever | Akto's runtime crashed | `docker compose restart akto-runtime` |
| Burp extension can't connect | URL mismatch | Verify Burp extension config matches `:9091/api/ingest` |

## Sources

- **Akto repo**: `sources/perimeter/akto/README.md`
- **Akto docs**: https://docs.akto.io
- **Deep-dive analysis**: [`../../reports/api-security.md`](../../reports/api-security.md) §"Akto"

## Live demo on slide 13?

**Don't live-demo Akto** on stage. The deployment time (3+ min) and dashboard UX dependencies make it fragile. Show a **pre-recorded 60-second clip** of:

1. The dashboard with crAPI's API inventory visible (8-12 endpoints).
2. A test run showing 40+ findings being discovered.
3. A drill-down into one BOLA finding showing the exact request/response.

The live demo slot belongs to Hadrian (scenario 04). Akto's role in the talk is "if you need broader coverage + dashboard, this is the platform; if you need depth + CI integration, prefer Hadrian."
