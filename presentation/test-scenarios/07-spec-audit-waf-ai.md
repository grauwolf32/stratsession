# 07 · Spec audit + WAF + AI-vuln-research

**Slide reference**: 16, 18, 20 · **Estimated time**: 60+ minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md), OpenAPI spec from scenario 04

Three smaller scenarios in one file because each is fast and they're each tied to one or two slides.

---

## Part A — Spec audit with Cherrybomb

**Slide reference**: 16 · **Estimated time**: 10 minutes

### Goal

Audit crAPI's OpenAPI spec for design-level flaws **before** running any live test. This catches issues that schema-aware fuzzers (Schemathesis, RESTler) would never see because they assume the spec is well-formed.

### Tool

| Tool | Submodule |
|---|---|
| **Cherrybomb** | [`../../sources/perimeter/cherrybomb`](../../sources/perimeter/cherrybomb) |

### Run

```bash
# From the cloned source (already built in scenario 00)
cd /home/ruslan/src/stratsession/sources/perimeter/cherrybomb
./target/release/cherrybomb oas validate -f /tmp/crapi-openapi.yaml -v warn

# Or with the CLI directly
cherrybomb oas validate -f /tmp/crapi-openapi.yaml -v all
```

### What Cherrybomb finds

- Endpoints declared but missing `security` definitions
- Operations without `responses` declarations
- Path parameters without type constraints
- Response bodies lacking schemas
- Inconsistent error response shapes across operations
- Required headers not declared in `parameters`
- HTTP methods that ignore the request body (PUT/POST without bodies)
- Sensitive parameter names without `format: password` markers

### Why it matters

Cherrybomb catches **spec-design bugs that propagate into live vulnerabilities**. Example pattern: an endpoint declares no security, but in production it actually requires auth — meaning the spec is wrong, downstream code-generators emit wrong client code, and developers misunderstand the contract. Result: real auth bugs that are spec-author's fault, not implementation-author's.

### Compare against Hadrian

- **Cherrybomb**: spec-level static check. No network calls. Fast.
- **Hadrian**: live-target dynamic check. Network calls. Slower but verifies behavior.

The two are complementary: run Cherrybomb in CI on every spec change. Run Hadrian against the deployed API on every deploy. They catch different bug classes.

### Sources

- **Cherrybomb repo**: `sources/perimeter/cherrybomb/README.md`
- **Deep-dive**: [`../../reports/api-security.md`](../../reports/api-security.md) §"Cherrybomb"

---

## Part B — WAF defense + bypass testing

**Slide reference**: 20 · **Estimated time**: 20 minutes

### Goal

1. Deploy **Coraza + OWASP CRS** as a WAF in front of crAPI.
2. Show that common attack payloads (SQL injection, command injection) are blocked.
3. Probe for **WAFFLED-class parsing-discrepancy bypasses** (2025-2026 research direction).

### Tools

| Tool | Submodule | Role |
|---|---|---|
| **Coraza** | [`../../sources/appsec/coraza`](../../sources/appsec/coraza) (cross-listed) | WAF engine |
| **OWASP CRS** | [`../../sources/appsec/coreruleset`](../../sources/appsec/coreruleset) (cross-listed) | Rule set |

### Deploy Coraza in front of crAPI

Easiest: use the **Caddy + Coraza** plugin.

```bash
# Pull the prebuilt Caddy-Coraza image (or build from sources/appsec/coraza)
docker run -d --rm \
  --name coraza-waf \
  --network stratlab \
  -p 8080:8080 \
  -v /home/ruslan/src/stratsession/sources/appsec/coreruleset:/etc/crs:ro \
  -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro \
  caddy/caddy:latest

# /tmp/Caddyfile contents:
cat > /tmp/Caddyfile <<'EOF'
{
  order coraza_waf before reverse_proxy
}
:8080 {
  coraza_waf {
    include /etc/crs/crs-setup.conf.example
    include /etc/crs/rules/*.conf
    directives `
      SecRuleEngine On
      SecRequestBodyAccess On
      SecResponseBodyAccess Off
      SecAuditEngine RelevantOnly
      SecAuditLog /var/log/coraza-audit.log
    `
  }
  reverse_proxy http://172.30.0.10:8888
}
EOF
```

Now crAPI is at `http://localhost:8080` (proxied through Coraza+CRS) and `http://localhost:8888` (direct).

### Verify the WAF blocks attacks

```bash
# Direct (no WAF) — succeeds
curl -i "http://localhost:8888/identity/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin' OR 1=1--\",\"password\":\"x\"}"
# Expected: 400 or 401 from crAPI

# Through WAF — blocked
curl -i "http://localhost:8080/identity/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin' OR 1=1--\",\"password\":\"x\"}"
# Expected: 403 Forbidden from Coraza/CRS

# Verify the audit log shows the block
docker exec coraza-waf tail -5 /var/log/coraza-audit.log
```

### Probe for parsing-discrepancy bypasses (advanced)

The **WAFFLED research** (arxiv 2503.10846, 2025) demonstrated 1,207 bypasses across 5 commercial WAFs by exploiting parsing differences between WAF and upstream app.

Example probe — Coraza parses multipart/form-data differently than Django:

```bash
# Use a boundary mismatch
curl -i "http://localhost:8080/identity/api/auth/login" \
  -H 'Content-Type: multipart/form-data; boundary=----X' \
  --data-binary $'------X\r\nContent-Disposition: form-data; name="email"\r\n\r\nadmin\' OR 1=1--\r\n------X--\r\n'

# Or content-type confusion
curl -i "http://localhost:8080/identity/api/auth/login" \
  -H "Content-Type: text/xml" \
  -d "<email>admin' OR 1=1--</email><password>x</password>"
```

If the WAF treats the body as opaque and the app parses it differently, the malicious payload gets through. **This is the active research area for WAF testing in 2026**, but mostly research-stage; no fully-OSS automated WAFFLED-style tester exists yet.

### Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Caddy fails to load CRS | Path mismatch | Ensure `/etc/crs/crs-setup.conf.example` exists in the volume |
| All requests blocked | Paranoia level too aggressive | Lower default: edit `crs-setup.conf` and set `tx.paranoia_level=1` |
| Audit log empty | `SecAuditEngine` off | Set `SecAuditEngine On` |
| WAF lets attacks through | CRS rules disabled | `docker exec coraza-waf cat /etc/caddy/Caddyfile | grep -i crs` |

### Sources

- **Coraza deep-dive**: [`../../reports/waf.md`](../../reports/waf.md) §"Coraza"
- **CRS deep-dive**: [`../../reports/waf.md`](../../reports/waf.md) §"OWASP Core Rule Set"
- **WAFFLED paper**: https://arxiv.org/abs/2503.10846 (2025) — research-stage, not yet productized

---

## Part C — AI-assisted vuln research at the perimeter

**Slide reference**: 18 · **Estimated time**: 30-60 minutes · **Note**: this is an *advanced/optional* scenario

### Goal

Run **Buttercup** (Trail of Bits' AIxCC CRS) against the source code of a service crAPI uses. Show that AI-driven CRS can find + auto-patch vulns in C/Java code that perimeter scanners can't see.

### Tools

| Tool | Submodule | Role |
|---|---|---|
| **Buttercup** | [`../../sources/appsec/buttercup`](../../sources/appsec/buttercup) (cross-listed) | Full CRS |
| **Seclab Taskflow Agent** | [`../../sources/appsec/seclab-taskflow-agent`](../../sources/appsec/seclab-taskflow-agent) | YAML-driven agentic workflow |

### Constraints

- Buttercup requires **OSS-Fuzz-compatible C or Java** projects.
- crAPI is Python/Go/Java; only its **Java microservice** is a candidate.
- Min spec: 8 CPU / 16 GB RAM / 100 GB disk / OpenAI or Anthropic key.
- Default LLM budget: $20/run. **Verify before running**.

### Buttercup against an OSS-Fuzz C target (simpler than Java)

For a demo, use the **example-libpng** target Trail of Bits ships:

```bash
cd /home/ruslan/src/stratsession/sources/appsec/buttercup

# Set up the environment (one-time)
make setup-local

# Configure LLM provider (one is enough; both better)
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export LLM_BUDGET_USD=10   # safety cap

# Deploy
make deploy

# Wait for all pods to be Ready (3-5 minutes)
make status

# Send a known-vulnerable example target
make send-libpng-task

# Watch for findings + patches
make web-ui
# Open http://localhost:31323 in browser
```

Expected: Buttercup discovers a known libpng vuln + generates a patch in ~5-15 minutes (LLM-cost-dependent).

### Seclab Taskflow Agent — lighter-weight alternative

If Buttercup is too heavy, demonstrate Seclab Taskflow Agent's CodeQL+LLM workflow:

```bash
cd /home/ruslan/src/stratsession/sources/appsec/seclab-taskflow-agent

# Install
python -m venv .venv && source .venv/bin/activate
pip install hatch && hatch build

# Configure LLM
export AI_API_TOKEN=$ANTHROPIC_API_KEY   # or OpenAI
export AI_API_ENDPOINT=https://models.github.ai/inference   # if using GitHub Models

# Run the bundled CVE-2023-2283 example workflow
hatch run main -t examples.taskflows.CVE-2023-2283

# Or, write a custom taskflow for crAPI's Java microservice
cat > /tmp/crapi-java-audit.yaml <<'EOF'
seclab-taskflow-agent:
  version: "1.0"
  filetype: taskflow

taskflow:
  - task:
      must_complete: true
      agents:
        - seclab_taskflow_agent.personalities.java_auditer
      user_prompt: |
        Audit /path/to/crapi/java/services for these patterns:
          1. SQL queries assembled by string concatenation
          2. Deserialization of untrusted bytes (XMLDecoder, ObjectInputStream)
          3. Reflective method invocation on user-controlled class names
        Report findings in CWE-tagged format.
      toolboxes:
        - seclab_taskflow_agent.toolboxes.codeql
EOF

hatch run main -t /tmp/crapi-java-audit
```

### What this proves to the audience

The slide-18 message: **AI-driven vuln research at the perimeter is operational, not research.**

- Buttercup demonstrated 28 bugs / 20 CWEs / 90% accuracy at **$181/point** on AIxCC.
- Both tools are OSI-licensed and runnable today.
- Cost is bounded (`LLM_BUDGET_USD`) and configurable.
- Output is auditable — generated patches and findings are readable artifacts.

### Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `make deploy` fails | Docker resources too low | Increase Docker Desktop / Colima allocation to 6 CPU / 10 GB |
| Buttercup hangs at "fuzzing" | No fuzzing harness in target | Choose an OSS-Fuzz-compatible target |
| Taskflow Agent "API key not authorized" | Wrong endpoint for token | Match `AI_API_ENDPOINT` to provider docs |
| LLM cost spike | Budget cap missing | Always set `LLM_BUDGET_USD` |

### Sources

- **Buttercup README**: `sources/appsec/buttercup/README.md`
- **Taskflow Agent README**: `sources/appsec/seclab-taskflow-agent/README.md`
- **Deep-dive analysis**: [`../../reports/ai-vuln-research.md`](../../reports/ai-vuln-research.md)
- **AIxCC results**: https://www.darpa.mil/news/2025/aixcc-results
- **OpenSSF SOSS podcast E53**: Trail of Bits' deployment journey

### Live demo on slide 18?

**Don't live-demo Buttercup**. Cost, time, and complexity make it unreliable. Show a 90-second pre-recorded clip of:

1. `make deploy` finishing successfully
2. `make send-libpng-task` submitting a task
3. Web UI showing the task progressing through fuzzing → analysis → patch
4. A diff showing the auto-generated patch

If you must live-demo: run Seclab Taskflow Agent's `examples.taskflows.echo` (60 seconds, no real audit, just shows the runtime + LLM call works).

---

## Summary of this combined file

Three smaller scenarios because each maps to one or two slides at most:

- **Part A — Cherrybomb** (slide 16, 10 min): static OpenAPI spec audit
- **Part B — Coraza + CRS + bypass probes** (slide 20, 20 min): WAF deployment + testing
- **Part C — Buttercup + Taskflow Agent** (slide 18, 30-60 min): AI-driven vuln research

All three are runnable; Part B is the most likely to work live on stage; Part C is the most impressive but the most fragile.
