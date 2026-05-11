# 05 · API fuzzing — Schemathesis + RESTler

**Slide reference**: 14, 15 · **Estimated time**: 30-60 minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md), OpenAPI spec from [`04-api-discovery-authz.md`](./04-api-discovery-authz.md)

## Goal

Show the **two complementary** API fuzzing approaches alongside Hadrian's authZ-testing:

- **Schemathesis** — property-based fuzzing: generates thousands of inputs that violate schema constraints to find input-validation bugs.
- **RESTler** — stateful fuzzing: chains producer→consumer requests to find logic bugs in multi-step flows.

Hadrian + Schemathesis + RESTler together cover the OWASP API Top 10 with the depth no single tool provides.

## Tools

| Tool | Submodule | Distinct from Hadrian |
|---|---|---|
| **Schemathesis** v4.18+ | [`../../sources/perimeter/schemathesis`](../../sources/perimeter/schemathesis) | Input validation bugs (not authZ) |
| **RESTler** | [`../../sources/perimeter/restler-fuzzer`](../../sources/perimeter/restler-fuzzer) | Multi-step CRUD logic bugs |

## Inputs

- OpenAPI spec from scenario 04: `/tmp/crapi-openapi.yaml`
- Auth tokens from scenario 04: `$VICTIM_TOKEN`, `$ATTACKER_TOKEN`

## Scenario A — Schemathesis property-based fuzzing

Schemathesis generates inputs from the OpenAPI schema, then checks each response satisfies invariants (status codes, content types, schema compliance).

### Basic run

```bash
schemathesis run /tmp/crapi-openapi.yaml \
  --base-url http://localhost:8888 \
  --auth-type bearer --header "Authorization: Bearer ${VICTIM_TOKEN}" \
  --checks all \
  --max-examples 50 \
  --workers 4
```

**What it tests**:
- Schema compliance — does response match the declared schema?
- Status code consistency — is `404` actually for missing resources?
- Server stability — do malformed inputs cause 500 errors?
- Header types — content-type / charset declarations match body?

### Negative testing (new in v4)

```bash
schemathesis run /tmp/crapi-openapi.yaml \
  --base-url http://localhost:8888 \
  --auth-type bearer --header "Authorization: Bearer ${VICTIM_TOKEN}" \
  --mode negative \
  --max-examples 100
```

`--mode negative` *intentionally* violates schema constraints (wrong types, missing required fields, oversized values, invalid enums). Catches "API claims input validation, but actually accepts invalid data."

### Stateful workflows (auto-discovery)

```bash
schemathesis run /tmp/crapi-openapi.yaml \
  --base-url http://localhost:8888 \
  --auth-type bearer --header "Authorization: Bearer ${VICTIM_TOKEN}" \
  --hypothesis-deadline 5000 \
  --hypothesis-suppress-health-check filter_too_much \
  --workers 4
```

Schemathesis infers `openapi.links` between operations and tests state transitions. With crAPI: create user → log in → access resources, in sequence.

### Custom checks

```bash
# Property: every user-data response must NOT include `latitude` or `longitude`
cat > /tmp/schemathesis-checks.py <<'EOF'
import schemathesis

@schemathesis.check
def no_location_leak(response, case):
    if response.headers.get("content-type", "").startswith("application/json"):
        body = response.text
        if "latitude" in body or "longitude" in body:
            raise AssertionError(f"Location data leaked: {response.url}")
EOF

schemathesis run /tmp/crapi-openapi.yaml \
  --base-url http://localhost:8888 \
  --auth-type bearer --header "Authorization: Bearer ${VICTIM_TOKEN}" \
  --hypothesis-suppress-health-check filter_too_much \
  --checks no_location_leak \
  --pre-run /tmp/schemathesis-checks.py
```

### Expected findings against crAPI

- Multiple `5xx` from malformed JSON bodies
- Schema/response mismatches (some endpoints declare schema but return extra fields)
- Possible information disclosure (Django debug-mode error responses)

### Schemathesis vs Hadrian

| Class of bug | Schemathesis | Hadrian |
|---|---|---|
| Schema/response mismatch | ✅ headline feature | ❌ |
| 500 on malformed JSON | ✅ | ❌ |
| BOLA / cross-user access | ❌ no concept of roles | ✅ headline feature |
| BFLA / privilege escalation | ❌ | ✅ |
| Excessive data exposure | partial (with custom checks) | ✅ |
| API rate limiting | ❌ | partial |

Use both. Don't choose one.

## Scenario B — RESTler stateful fuzzing

RESTler's signature feature: **producer-consumer dependency inference** — it reads the OpenAPI spec, figures out which endpoint produces a resource the next endpoint consumes, and chains them automatically.

### Build RESTler Docker image

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/restler-fuzzer
docker build -t restler:local -f Dockerfile .
```

### Compile the OpenAPI spec into a fuzzing grammar

```bash
mkdir -p /tmp/restler-output && cd /tmp/restler-output

docker run --rm -it \
  -v /tmp:/work \
  --network stratlab \
  restler:local \
  /restler_bin/restler compile \
  --api_spec /work/crapi-openapi.yaml \
  --target_dir /work/restler-output
```

**Output**: `Compile/grammar.py` (RESTler-internal representation) + dependency graph showing inferred producer→consumer relationships.

### Run a smoke test (quick)

```bash
docker run --rm -it \
  -v /tmp:/work \
  --network stratlab \
  restler:local \
  /restler_bin/restler test \
  --grammar_file /work/restler-output/Compile/grammar.py \
  --target_ip 172.30.0.10 --target_port 8888 \
  --token_refresh_command "echo authentication=Bearer $VICTIM_TOKEN" \
  --time_budget 0.05    # 3 minutes
```

`smoke test` mode sends one of each request type, verifies the spec is correct, then exits. Use to debug spec issues before running fuzzing.

### Run actual fuzzing

```bash
docker run --rm -it \
  -v /tmp:/work \
  --network stratlab \
  restler:local \
  /restler_bin/restler fuzz \
  --grammar_file /work/restler-output/Compile/grammar.py \
  --target_ip 172.30.0.10 --target_port 8888 \
  --token_refresh_command "echo authentication=Bearer $VICTIM_TOKEN" \
  --time_budget 1.0    # 1 hour
```

`fuzz` mode explores the request space using producer-consumer relationships. Bugs found are logged as `bugs/` files in the output directory.

### Expected findings

- 500 errors on resource creation with malformed-but-valid-shape inputs
- Cases where a `DELETE /users/{id}` succeeds for a non-existent user (idempotency violations, sometimes auth bypass)
- "Logic bugs that take a sequence to reach" — e.g., create vehicle → modify with invalid mechanic_id → server crashes

### RESTler vs Schemathesis

| | Schemathesis | RESTler |
|---|---|---|
| Approach | Property-based, schema-constraint violations | Stateful, producer-consumer sequences |
| Stateful workflows | Some (via OpenAPI links) | First-class, headline feature |
| LLM-augmented inputs | v4 has experimental | No |
| Setup complexity | Low (pip install + run) | Medium (compile grammar first) |
| Output format | Console / JSON / JUnit | Internal logs + bugs/ |
| When most useful | Public APIs, contract validation | Stateful CRUD APIs, sequence bugs |
| Active dev as of 2026 | Yes, v4.18+ | Yes, Microsoft Research continues; RAFT archived |

## Scenario C — Run all three (Schemathesis, RESTler, Hadrian) and consolidate

```bash
# Schemathesis — input validation
schemathesis run /tmp/crapi-openapi.yaml \
  --base-url http://localhost:8888 \
  --header "Authorization: Bearer ${VICTIM_TOKEN}" \
  --max-examples 100 \
  --report /tmp/schemathesis.junit.xml \
  --report-format junit-xml

# RESTler — stateful (already running in background or earlier)
# Output: /tmp/restler-output/Test/RestlerResults/<timestamp>/bug_buckets/

# Hadrian — authZ
hadrian test rest \
  --api /tmp/crapi-openapi.yaml \
  --roles /tmp/roles.yaml \
  --auth /tmp/auth.yaml \
  --output json --output-file /tmp/hadrian.json

# All three results can be imported into DefectDojo (cross-listed under sources/appsec/)
```

**Combined coverage**: schema mismatches + stateful logic bugs + authZ violations = ~80% of OWASP API Top 10 covered automatically. The remaining 20% (business-logic abuse, supply-chain) requires manual review.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Schemathesis "HealthCheck filtering" warnings | crAPI's schema is restrictive | Add `--hypothesis-suppress-health-check filter_too_much` |
| Schemathesis hangs on `/community/api/v2/coupon/*` | Auth flow breaks | Add `--auth-refresh-token-command` for periodic token refresh |
| RESTler compile fails | YAML/JSON edge case | Convert to JSON first: `python -c "import yaml,json; print(json.dumps(yaml.safe_load(open('crapi-openapi.yaml'))))" > openapi.json` |
| RESTler can't reach 172.30.0.10 | Not on `stratlab` Docker network | Add `--network stratlab` to `docker run` |
| Both tools report 0 bugs | Spec doesn't cover real endpoints | Re-run Vespasian with `--depth 5 --max-pages 100` for more coverage |

## Sources

- **Schemathesis docs**: https://schemathesis.io
- **RESTler README**: `sources/perimeter/restler-fuzzer/README.md`
- **RESTler paper**: Microsoft Research — "RESTler: Stateful REST API Fuzzing"
- **Deep-dive analysis**: [`../../reports/api-security.md`](../../reports/api-security.md) §"Schemathesis", §"RESTler"

## What this proves to the audience

The slide-14/15 story is: **API fuzzing has matured into two complementary patterns**.
- Schemathesis = property-based, schema-aware, easy to start.
- RESTler = stateful, sequence-aware, deeper exploration.

Both are OSS, both are active, both produce findings against a public vulnerable target in minutes. Combined with Hadrian's authZ testing, this is the strongest *OSS* API-security testing capability ever assembled.
