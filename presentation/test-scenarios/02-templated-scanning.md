# 02 · Templated scanning + AI template generation

**Slide reference**: 8 · **Estimated time**: 15-30 minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md)

## Goal

Show three things, in order of increasing 2026-novelty:

1. **Classic Nuclei** — templated vuln scan against crAPI
2. **Nuclei AI flag** (`-ai`) — generate a template from natural language and run it
3. **nuclei-templates-ai** — use AI-generated templates for recent CVEs not yet community-covered

## Tools used

| Tool | Role | Submodule |
|---|---|---|
| `nuclei` | Templated scanner (v3.8+) | [`../../sources/perimeter/nuclei`](../../sources/perimeter/nuclei) |
| `nuclei-templates` | 12K+ community templates | [`../../sources/perimeter/nuclei-templates`](../../sources/perimeter/nuclei-templates) |
| `nuclei-ai-extension` | Browser ext for template generation | [`../../sources/perimeter/nuclei-ai-extension`](../../sources/perimeter/nuclei-ai-extension) |
| `nuclei-templates-ai` | AI-generated templates for new CVEs | [`../../sources/perimeter/nuclei-templates-ai`](../../sources/perimeter/nuclei-templates-ai) |

## Scenario A — Classic Nuclei against crAPI

```bash
# Ensure templates are up to date
nuclei -update-templates

# Scan crAPI with the default suite (slow — ~5 min)
nuclei -u http://localhost:8888 -silent -o /tmp/nuclei-crapi.txt

# Quick targeted scan: only HTTP misconfig category (~30 sec)
nuclei -u http://localhost:8888 \
  -tags misconfig \
  -severity info,low,medium,high,critical \
  -silent \
  -o /tmp/nuclei-crapi-misconfig.txt

wc -l /tmp/nuclei-crapi-misconfig.txt
cat /tmp/nuclei-crapi-misconfig.txt
```

**Expected findings on crAPI**:
- exposed `.env` or debug routes (varies by version)
- CORS misconfigurations
- missing security headers
- info-level fingerprints (Django, microservices)

## Scenario B — AI template generation (live demo for slide 8)

Nuclei v3.8 (April 2026) added `-ai` for natural-language template generation. Requires API key:

```bash
export NUCLEI_AI_API_KEY="${OPENAI_API_KEY}"

# Generate a template from a plain-English description
nuclei -ai "find APIs that return 500 errors on malformed JSON" \
  -u http://localhost:8888/identity/api/v2/user \
  -silent

# Or save the generated template for later reuse
nuclei -ai "detect Spring Boot actuator endpoints with no auth" \
  -ai-template-output /tmp/generated-template.yaml

cat /tmp/generated-template.yaml
```

The `-ai` workflow:
1. Sends your natural-language description to the model
2. Model emits a Nuclei YAML template
3. Nuclei executes the template against the target
4. (Optional) `-ai-template-output` saves the generated YAML

**Demo talking points**:
- 2024-era equivalent: "open template repo on GitHub → find one similar → copy-paste → modify → save → run." 10+ minutes.
- 2026 equivalent: 8 seconds.
- The generated template is real YAML you can audit/edit/commit; it's not a black box.

## Scenario C — nuclei-templates-ai (AI-generated CVE templates)

The `projectdiscovery/nuclei-templates-ai` repo is a *parallel* template library where AI is used to generate templates for CVEs *before* the community gets to them. Useful for "I just heard about CVE-2026-X, no community template yet, but I need to scan tonight."

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/nuclei-templates-ai

# List recent AI-generated templates
ls cves/2026/ | tail -20

# Pick one and run it
TEMPLATE_PATH=$(ls cves/2026/*.yaml | tail -1)
nuclei -u http://localhost:8888 -t "$TEMPLATE_PATH" -silent
```

**Important caveat**: AI-generated templates can have higher false-positive rates than community-validated ones. The repo is *complementary* to community templates, not replacement. Verify findings.

## Scenario D — nuclei-ai-extension (browser-based template generation)

The browser extension lets you generate a template **directly from a vulnerable HTTP request you're looking at in DevTools or Burp/Caido**. Installation:

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/nuclei-ai-extension
# Load as unpacked extension in Chrome:
#   chrome://extensions → "Load unpacked" → select the directory
```

Once installed:
1. Browse crAPI in Chrome
2. Find a request that returns something interesting in DevTools Network tab
3. Click the Nuclei AI extension icon
4. Describe what you want to detect: "find this endpoint exposed without authentication"
5. Extension generates the YAML; copy → save → `nuclei -t saved.yaml -u <target>`

This is the "I found a bug, can I template it instantly" workflow. Pairs especially well with Caido (scenario 03).

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `nuclei -update-templates` hangs | GitHub rate limit | Wait + retry; or set `-update-template-dir` to a local path |
| `nuclei -ai` returns "API key missing" | Env var not set | `export NUCLEI_AI_API_KEY="$OPENAI_API_KEY"` |
| Generated template doesn't match anything | Description too vague | Make the prompt very specific: include path, method, expected response shape |
| Browser extension doesn't load | Manifest v3 issue | Check Chrome version ≥ 110; check extension page for errors |

## Sources

- **Nuclei changelog**: https://github.com/projectdiscovery/nuclei/releases (v3.8.0, April 2026)
- **`-ai` feature docs**: `nuclei -h | grep -A3 ai`
- **Templates-AI README**: `sources/perimeter/nuclei-templates-ai/README.md`

## Live demo script (for slide 8, 90 seconds)

```bash
# 0s
clear
echo "Classic Nuclei scan…"
nuclei -u http://localhost:8888 -tags misconfig -silent | head -5
# 20s
echo
echo "Now AI template generation…"
nuclei -ai "detect missing security headers on this API" \
  -u http://localhost:8888 \
  -ai-template-output /tmp/headers.yaml -silent
# 60s
echo
echo "Generated template:"
cat /tmp/headers.yaml | head -25
# 80s
echo "From idea to running scan in under a minute."
```

This script gives ~3 distinct beats for the audience: classic → AI generates → AI's output is readable YAML. Same tool, transformation through 2026 features.
