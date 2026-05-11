# 04 · API discovery + authZ — Vespasian + Hadrian

**Slide reference**: 10, 11, **12 (live demo candidate)** · **Estimated time**: 20-40 minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md)

## Goal

Run the full Praetorian discover-then-test workflow against crAPI:

1. **Vespasian** observes traffic from a crAPI session → generates OpenAPI 3.0 spec
2. **Hadrian** consumes the spec + role definitions → tests OWASP API Top 10 authorization
3. Reproduce Praetorian's claim: **3 BOLA findings in crAPI in <60 seconds**

This is the **headline live-demo scenario** for slide 12.

## Tools

| Tool | Role | Submodule |
|---|---|---|
| **Vespasian** | API discovery + spec generation | [`../../sources/appsec/vespasian`](../../sources/appsec/vespasian) (cross-listed) |
| **Hadrian** | Role-based authZ testing | [`../../sources/appsec/hadrian`](../../sources/appsec/hadrian) (cross-listed) |
| **crAPI** | Target | [`../../sources/perimeter/crapi`](../../sources/perimeter/crapi) |

## Prep — crAPI users

In crAPI's web UI (`http://localhost:8888`):

1. Sign up as **`victim@stratlab.local`** with password `Victim123!`
2. Add a vehicle to the victim account (gives the account a resource to attack)
3. Sign out
4. Sign up as **`attacker@stratlab.local`** with password `Attacker123!`
5. Capture both bearer tokens from DevTools → Network → Headers. Save:

```bash
export VICTIM_TOKEN="eyJhbGciOiJIUzUx..."
export ATTACKER_TOKEN="eyJhbGciOiJIUzUx..."
```

## Scenario A — Vespasian crawl + spec generation (10 minutes)

```bash
# Crawl crAPI with an authenticated victim session
vespasian scan http://localhost:8888 \
  -H "Authorization: Bearer ${VICTIM_TOKEN}" \
  --dangerous-allow-private \
  --depth 3 --max-pages 50 \
  -o /tmp/crapi-openapi.yaml

# Inspect the generated spec
head -50 /tmp/crapi-openapi.yaml
grep -c "operationId:" /tmp/crapi-openapi.yaml    # discovered endpoints
```

**Expected output**:
- ~20-40 endpoints discovered across `/identity/api/v2/*`, `/workshop/api/*`, `/community/api/v2/*`
- Schema inference for request/response bodies
- Path parameters auto-normalized (`/users/{userId}`)

If crawl misses GraphQL endpoints, run separately with `--api-type graphql` and combine.

**Alternative**: import a Burp/HAR capture instead of crawling:

```bash
# In Burp/Caido: do manual auth flow + click around, export sitemap as XML
vespasian import burp burp-export.xml -o /tmp/capture.json
vespasian generate rest /tmp/capture.json -o /tmp/crapi-openapi.yaml
```

This is the recommended path for SPAs that Vespasian's Katana crawl misses.

## Scenario B — Hadrian config generation (5 minutes)

Hadrian needs three config files: spec (from Vespasian), `roles.yaml`, `auth.yaml`.

### Option 1 — Hadrian's Claude Code skill (recommended)

```bash
# Load Hadrian as a Claude Code plugin
cd /home/ruslan/src/stratsession/sources/appsec/hadrian
claude --plugin-dir .

# Then in Claude Code:
# "Generate Hadrian auth.yaml and roles.yaml from /tmp/crapi-openapi.yaml"
```

The skill at `skills/hadrian-openapi-authz/` reads the spec and proposes role + auth configurations.

### Option 2 — Manual

```bash
# /tmp/roles.yaml
cat > /tmp/roles.yaml <<EOF
roles:
  - name: victim
    permissions:
      - "read:user:own"
      - "write:user:own"
      - "delete:user:own"
  - name: attacker
    permissions:
      - "read:user:own"
      - "write:user:own"
      - "delete:user:own"
EOF

# /tmp/auth.yaml
cat > /tmp/auth.yaml <<EOF
auth_methods:
  - name: victim
    type: bearer
    token: "${VICTIM_TOKEN}"
  - name: attacker
    type: bearer
    token: "${ATTACKER_TOKEN}"
EOF
```

## Scenario C — Hadrian test run (5-10 minutes)

```bash
# Brute-force run: every endpoint × every template × every role
hadrian test rest \
  --api /tmp/crapi-openapi.yaml \
  --roles /tmp/roles.yaml \
  --auth /tmp/auth.yaml \
  --output terminal

# With LLM planner: prioritize attacks before brute-force
hadrian test rest \
  --api /tmp/crapi-openapi.yaml \
  --roles /tmp/roles.yaml \
  --auth /tmp/auth.yaml \
  --planner --planner-provider anthropic \
  --output terminal

# Planner-only mode: faster, only runs LLM-chosen targets
hadrian test rest \
  --api /tmp/crapi-openapi.yaml \
  --roles /tmp/roles.yaml \
  --auth /tmp/auth.yaml \
  --planner --planner-only \
  --output json --output-file /tmp/hadrian-report.json
```

**Expected findings** (per Praetorian's reproducible claim):
- **CRITICAL — BOLA**: attacker can read victim's user profile (`GET /identity/api/v2/user/{id}` with attacker token returns victim data)
- **CRITICAL — BOLA**: attacker can read victim's vehicle (`GET /identity/api/v2/vehicle/{id}`)
- **HIGH — Excessive Data Exposure**: API returns sensitive fields (e.g., `latitude`, `longitude`, `vin`) that shouldn't reach the UI

The three-phase mutation test in action — Hadrian's distinctive feature:

```
Phase 1: SETUP    → victim user creates a "vehicle" resource; store the vehicle_id
Phase 2: ATTACK   → attacker tries DELETE /identity/api/v2/vehicle/<vehicle_id>
Phase 3: VERIFY   → victim re-fetches the vehicle; if 404, deletion succeeded
```

Without phase 3, you'd report a false positive whenever the API returns `200 OK` but silently ignores the unauthorized request. With phase 3, Hadrian confirms actual state change.

## Scenario D — Live demo script for slide 12 (60 seconds)

```bash
# 0s — set up terminal
clear
echo "Discovering crAPI's API surface…"

# 3s
vespasian scan http://localhost:8888 \
  -H "Authorization: Bearer ${VICTIM_TOKEN}" \
  --dangerous-allow-private \
  --depth 2 --max-pages 20 \
  -o /tmp/spec.yaml 2>/dev/null
echo "Generated $(grep -c operationId /tmp/spec.yaml) endpoints"

# 15s
echo "Now testing authorization across all endpoints…"
hadrian test rest \
  --api /tmp/spec.yaml \
  --roles /tmp/roles.yaml \
  --auth /tmp/auth.yaml \
  --planner --planner-only \
  --output terminal 2>&1 | head -25

# 50s — expect findings visible
```

Talking points during demo:
- "In 60 seconds: discover the API, generate a spec, test it for authZ bugs."
- "Hadrian found these in crAPI; same templates run against your production API tomorrow."
- "Three-phase mutation means findings are verified, not just 200-OK guesses."

## Scenario E — Custom templates (advanced)

Hadrian's YAML template grammar is auditable + extensible. Example: add a template for a *crAPI-specific* business rule (e.g., "users shouldn't be able to apply other users' coupons"):

```bash
mkdir -p /tmp/custom-templates/rest/
cat > /tmp/custom-templates/rest/99-crapi-coupon-leak.yaml <<'EOF'
id: 99-crapi-coupon-leak
info:
  name: "crAPI — Coupon Code Brute Force"
  category: "API4:2023"
  severity: "HIGH"
  description: "crAPI's coupon endpoint can be brute-forced"
  test_pattern: "simple"
endpoint_selector:
  path: "/community/api/v2/coupon/validate-coupon"
  methods: ["POST"]
http:
  - method: "POST"
    path: "{{operation.path}}"
    body: |
      {"coupon_code": "TRAC075"}
detection:
  success_indicators:
    - type: status_code
      status_code: 200
EOF

# Run with custom template
HADRIAN_TEMPLATES=/tmp/custom-templates hadrian test rest \
  --api /tmp/spec.yaml --roles /tmp/roles.yaml --auth /tmp/auth.yaml
```

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Vespasian discovers 0 endpoints | Auth token expired / wrong | Re-capture token; verify in Caido it works |
| Vespasian misses GraphQL | Wrong API type | Re-run with `--api-type graphql` |
| Hadrian finds 0 BOLA | Roles not differentiated | Verify `attacker_permission_level: "lower"` matches a real role in `roles.yaml` |
| `--planner` errors with "No API key" | Env var missing | `export OPENAI_API_KEY=...` (or use `--planner-provider anthropic`) |
| Three-phase test fails on `VERIFY` step | crAPI's delete is async | Adjust template's `verify` step with delay |

## Sources

- **Vespasian README**: `sources/appsec/vespasian/README.md`
- **Hadrian README**: `sources/appsec/hadrian/README.md`
- **Hadrian tutorial**: https://github.com/praetorian-inc/hadrian/wiki/Tutorials
- **Praetorian crAPI demo claim**: "3 critical BOLAs in under 60 seconds"
- **Deep-dive analysis**: [`../../reports/api-security.md`](../../reports/api-security.md) §"Hadrian"

## What this proves to the audience

This is the deck's strongest single demo because:
1. **Vespasian + Hadrian is the most-novel new OSS tool pair of 2026** in this category.
2. **The 60-second-to-3-BOLAs claim is reproducible** on a public vulnerable target.
3. **The output is actionable**: every finding includes the exact HTTP request that demonstrated the vuln.
4. **The framework is extensible**: custom templates show this isn't a closed-box scanner.

After this demo, the audience should be asking "how do we get this on our production APIs by Q3?"
