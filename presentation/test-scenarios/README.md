# Test scenarios — index

Locally-runnable hands-on tests for every tool in [`../../sources/perimeter/`](../../sources/perimeter/), structured so you can demo any individual tool from the [slides](../slides.md) without the rest, or run the full chain end-to-end.

## Files

| File | What it covers | Slide reference | Time to run |
|---|---|---|---|
| [`00-environment-setup.md`](./00-environment-setup.md) | Docker network, crAPI, Juice Shop, WAF setup, tool installation | Slide 21, 27 | 15-30 min one-time |
| [`01-recon-chain.md`](./01-recon-chain.md) | `subfinder` → `httpx` → `naabu` → `katana` → `uncover` | Slides 6-7 | 10-20 min |
| [`02-templated-scanning.md`](./02-templated-scanning.md) | `nuclei`, `nuclei-ai-extension`, `nuclei-templates-ai` | Slide 8 | 15-30 min |
| [`03-modern-dast.md`](./03-modern-dast.md) | `caido` manual web pentest workflow | Slide 9 | 30-60 min |
| [`04-api-discovery-authz.md`](./04-api-discovery-authz.md) | `vespasian` + `hadrian` against crAPI | Slides 10-12 | 20-40 min |
| [`05-api-fuzzing.md`](./05-api-fuzzing.md) | `schemathesis` + `restler-fuzzer` | Slides 14-15 | 30-60 min |
| [`06-api-platform.md`](./06-api-platform.md) | `akto` end-to-end deployment | Slide 13 | 30-60 min |
| [`07-spec-audit-waf-ai.md`](./07-spec-audit-waf-ai.md) | `cherrybomb` spec audit + Coraza/CRS WAF + Buttercup/Taskflow Agent | Slides 16, 18, 20 | 60+ min |

## Tool → test scenario matrix

| Tool | Scenario file | What you'll verify |
|---|---|---|
| **subfinder** | 01-recon-chain | Discovers known subdomains for a target domain |
| **httpx** | 01-recon-chain | Probes alive hosts + tech fingerprint |
| **naabu** | 01-recon-chain | Lists open ports per host |
| **katana** | 01-recon-chain | Crawls SPAs and collects all URLs |
| **uncover** | 01-recon-chain | Search-engine-driven discovery via Shodan/Censys |
| **nuclei** | 02-templated-scanning | Templated CVE/misconfig scan against crAPI |
| **nuclei-ai-extension** | 02-templated-scanning | Generate a template from natural language description |
| **nuclei-templates-ai** | 02-templated-scanning | Use AI-generated templates for recent CVEs |
| **caido** | 03-modern-dast | Manual proxy-based web pentest workflow |
| **vespasian** *(in appsec)* | 04-api-discovery-authz | Capture crAPI traffic, generate OpenAPI 3.0 spec |
| **hadrian** *(in appsec)* | 04-api-discovery-authz | Run authZ tests + three-phase mutation test |
| **schemathesis** | 05-api-fuzzing | Property-based fuzzing against crAPI OpenAPI spec |
| **restler-fuzzer** | 05-api-fuzzing | Stateful API fuzzing against crAPI |
| **akto** | 06-api-platform | Deploy Akto, capture crAPI traffic, run 1000+ tests |
| **cherrybomb** | 07-spec-audit-waf-ai | Audit crAPI's OpenAPI spec for design flaws |
| **coraza + CRS** *(in appsec)* | 07-spec-audit-waf-ai | Deploy WAF in front of vulnerable app, test bypasses |
| **buttercup** *(in appsec)* | 07-spec-audit-waf-ai | AI-driven vuln discovery + patching against C/Java target |
| **seclab-taskflow-agent** *(in appsec)* | 07-spec-audit-waf-ai | YAML-driven CodeQL + LLM workflow |
| **OWASP crAPI** | 00-environment-setup | Vulnerable target running on localhost |

## Suggested running order

### For a full rehearsal (3-4 hours)

1. **00-environment-setup** — Docker network + crAPI + Juice Shop + WAF (30 min)
2. **01-recon-chain** — verify recon tools work (15 min)
3. **04-api-discovery-authz** — Vespasian → spec → Hadrian (40 min) ⭐ live-demo candidate
4. **05-api-fuzzing** — Schemathesis + RESTler (45 min)
5. **02-templated-scanning** — Nuclei + AI (30 min)
6. **06-api-platform** — Akto (45 min, runs in background while you do others)
7. **03-modern-dast** — Caido walkthrough (45 min)
8. **07-spec-audit-waf-ai** — Cherrybomb + WAF + Buttercup (60+ min)

Total: ~5 hours including reading. **Plan two evenings**, not one.

### For a 30-min smoke test before the talk

1. `make verify` (defined in `00-environment-setup.md`) — confirms environment is alive
2. Demo flow: scenario 01 (recon, 5 min) → scenario 04 (Hadrian, 5 min) → scenario 02 (Nuclei AI, 5 min)

If those three work, the deck is safe to present.

## Pre-flight checklist (run on the laptop you'll present from)

- [ ] Docker / Docker Compose installed and working
- [ ] Disk free ≥ 30 GB (Akto + crAPI + Buttercup are big)
- [ ] Internet (some tools fetch templates/vuln databases at runtime)
- [ ] LLM API keys configured for tools that need them (Nuclei AI, Hadrian planner, Buttercup, Taskflow Agent)
- [ ] OWASP crAPI runs and is reachable: `curl http://localhost:8888`
- [ ] OWASP Juice Shop runs and is reachable: `curl http://localhost:3000`
- [ ] All 15 perimeter submodules cloned: `git submodule status | grep perimeter | wc -l` returns `15`

## Safety notes

- **All scenarios target localhost-only services**: crAPI, Juice Shop, your own WAF lab.
- **Recon scenario (01)** is the only one that can target external hosts. Default examples in this folder use `example.com` (intentionally bland). **Never run subfinder/uncover/etc. against domains you don't own without written authorization.**
- **Akto deployment uses MongoDB**: don't expose its port to the network during the demo.
- **Buttercup uses commercial LLM APIs** ($-cost). The budget cap in its config defaults to $20/run; verify before running.

## Quick reference — common commands

```bash
# Run a specific scenario
cd /home/ruslan/src/stratsession/presentation/test-scenarios
cat 01-recon-chain.md   # or whichever

# Tear down everything
docker compose -f 00-environment-setup-compose.yml down -v
docker network prune -f

# Re-clone a submodule (if something broke during testing)
git submodule update --init sources/perimeter/<name>
```
