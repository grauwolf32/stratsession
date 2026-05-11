# Vulnerability management + SBOM — DefectDojo · Sunshine

These are different layers of the same problem ("what do I do with all these findings?"):

- **DefectDojo** is the *system of record* — multi-tool ingestion, dedup, triage, workflow, JIRA sync.
- **Sunshine** is a *focused viewer* — takes a CycloneDX SBOM and renders an actionable HTML visualization.

| | DefectDojo | Sunshine |
|---|---|---|
| What | DevSecOps / ASPM / vuln management platform | CycloneDX SBOM visualizer |
| Author | OWASP Flagship project | OWASP CycloneDX (Luca Capacci + Mattia Fierro) |
| Form factor | Django web app + REST API | Python CLI + standalone HTML web app |
| Language | Python (Django) | Python + HTML/JS |
| Repo size | 301 MB / 268 files (5,000 line `dojo/models.py`) | 412 KB / 8 files |
| Inputs | Outputs from 200+ scanners | Single CycloneDX JSON file |
| Outputs | Tickets, dashboards, JIRA sync, reports | Interactive HTML chart + table |
| OWASP status | Flagship | Project under CycloneDX |

The size asymmetry is informative: DefectDojo is a 12-year-old enterprise platform with a Django monolith mid-decomposition (you can see the in-progress modular reorganization in its `CLAUDE.md`); Sunshine is a focused new tool that does one thing well.

---

## DefectDojo — the OWASP flagship vuln-mgmt platform

DefectDojo is "what do I do with thousands of scanner findings from a dozen tools?" The novelty isn't conceptual (Nessus had this in 1998); it's the **scope of integrations and the OSS staying power**.

What it actually does, from the README:

> DefectDojo orchestrates **end-to-end security testing, vulnerability tracking, deduplication, remediation, and reporting**.

The non-obvious value is in three places:

1. **Scanner parser coverage.** DefectDojo includes parsers for ~200+ security tools — Trivy, Nuclei, Burp, ZAP, Nessus, OpenVAS, Bandit, Semgrep, Snyk, Checkov, Trufflehog, gitleaks, ECR, Anchore, Clair, the full SAST/SCA/DAST/secret/IaC universe. You pipe scanner output → DefectDojo → unified Finding objects. The maintainers update parsers as upstream output formats change.
2. **Deduplication is the operational killer feature.** Most teams' real pain isn't "scanner X reported a CVE"; it's "scanner X, Y, and Z all reported the same CVE 40 times across 12 projects, please give me 1 ticket." DefectDojo's dedup logic compares findings across imports and merges by configurable identity keys (CWE + component + location, etc.).
3. **State machine for findings.** Every finding has a lifecycle: active / under_review / under_defect_review / verified / accepted / false_positive / out_of_scope / duplicate / mitigated. With state transitions, due dates, SLA tracking, and notification hooks. This is what you'd build internally; DefectDojo gives it to you.

### What's structurally novel right now

The `CLAUDE.md` in the submodule shows DefectDojo is **mid-architectural rewrite**. The Django codebase is being decomposed from a monolithic `dojo/models.py` (4,973 lines!) into per-domain modules following the pattern of `dojo/url/` — `models.py`, `services.py`, `admin.py`, `queries.py`, `signals.py`, with separate `ui/` and `api/` subdirectories.

The reorganization playbook is unusually well-documented:

```
dojo/{module}/
├── models.py     # Domain models
├── admin.py      # Admin registrations
├── services.py   # Business logic (no HTTP concerns)
├── queries.py    # Complex DB aggregations
├── ui/           # Django views, forms, filters, urls
└── api/          # DRF serializers, viewsets, filters
```

The critical principle: **`services.py` is called by both `ui/views.py` and `api/views.py`** — business logic is centralized, presentation layers are thin. This is essentially Domain-Driven Design retrofitted onto an existing Django app.

Status as of the submodule snapshot:

| Module | Status |
|---|---|
| `url` | **Complete** (reference pattern) |
| `location` | **Complete** |
| `product_type`, `test`, `engagement`, `product`, `finding` | Partial |

This is a **two-year refactor in progress**. If you're forking or contributing, the `CLAUDE.md` Phase 0–9 playbook is the canonical guide.

### What DefectDojo is *not*

- Not a scanner. It consumes scanner output.
- Not a workflow tool by default — but it has hooks into Jira, GitHub Issues, GitLab Issues. You wire those up.
- Not a SOAR. No automated remediation, only ticketing.
- Not cheap to run at scale. The Django ORM has historically been the bottleneck; the ASPM workload generates a lot of database churn. The community version uses MySQL; the Pro edition has scalability features the OSS version doesn't.

### Pro vs. OSS

DefectDojo Inc. sells a Pro edition with a new UI, risk-based prioritization, additional connectors (ServiceNow, Azure DevOps, etc.), data enrichment, and managed SaaS. The community edition is OWASP-flagship and fully functional, just less polished. The split is similar to GitLab / Gitea / OpenProject — same project, two distribution tiers.

## Sunshine — actionable CycloneDX visualization

Sunshine is the *focused* counterpart. Sixteen lines of cogent value proposition: take a CycloneDX SBOM, produce an HTML file showing components, dependencies, vulnerabilities, and licenses, with the option to enrich with **EPSS** (Exploit Prediction Scoring System) and **CISA KEV** (Known Exploited Vulnerabilities catalog) data.

What's novel about Sunshine:

1. **Two deployment shapes, one codebase.**
   - **Web app**: serve the directory with `python3 -m http.server 8000`, open browser, upload SBOM. Processing is **all local in the browser** — nothing transmitted. Or use the hosted version at https://cyclonedx.github.io/Sunshine/.
   - **CLI**: `python sunshine.py -i sbom.json -o output.html -e` produces a standalone HTML.
2. **EPSS + CISA KEV enrichment is a one-flag operation.** `-e` enables it. The output then includes EPSS exploit probability and KEV active-exploitation flag per CVE. **This is the actionable part** — most SBOMs show you "you have CVE-2024-1234" but not "this is being actively exploited right now."
3. **Filter chains designed for triage.**
   - `-k` — only show vulnerabilities listed in CISA KEV
   - `-cs / -hs / -ms / -ls` — only critical / high / medium / low or above severity
   - `-c MIN_CVSS` — CVSS threshold
   - `-p MIN_EPSS` — EPSS threshold
   - `-n` — disable segment-count limits on charts (large SBOMs)
   These filters compose. You can produce "only KEV-listed vulnerabilities with EPSS ≥ 0.5 and CVSS ≥ 7.0" in one command.
4. **Self-contained HTML output.** No external assets, no JS frameworks loaded from CDN. You can email the HTML to a stakeholder and it renders on their laptop offline. Critical for air-gapped or audit-evidence scenarios.
5. **CycloneDX-native.** Not Trivy JSON, not Syft, not Grype — *CycloneDX 1.4+ JSON*. This is the format OWASP / industry standards have converged on for SBOMs. Sunshine assumes you've already produced a CycloneDX SBOM (Trivy, Syft, cyclonedx-cli, etc. all do this).
6. **License visualization.** Often missed in SBOM tooling — Sunshine shows component licenses alongside vulnerabilities. Useful for compliance review.
7. **Small, hackable.** 8 files. You can read the entire codebase in 15 minutes and modify the output format.

The strategic role: **Sunshine is the missing "what do I do with my SBOM" layer.** Most teams generate SBOMs (CRA compliance, US EO 14028, customer demands), store them in S3, and never look at them. Sunshine is the lightest-weight way to make that SBOM actionable for triage.

## How they fit together

| Question | Use |
|---|---|
| "We have 12 scanners and no central view." | DefectDojo |
| "Triage workflow with SLAs and JIRA sync" | DefectDojo |
| "AppSec posture dashboard across business units" | DefectDojo (or Pro) |
| "Customer asked for our SBOM and wants to know what's exploitable" | Sunshine |
| "Quick triage of a CycloneDX SBOM for a new project" | Sunshine |
| "Email an executive a one-page vuln-by-EPSS view" | Sunshine HTML output |

Reasonable architecture for a mid-sized AppSec team:

```
Scanners (Trivy, Semgrep, etc.) → Findings → DefectDojo (system of record)
                              ↘
                                CycloneDX SBOMs (Trivy generates these)
                                                                     ↘
                                                                       Sunshine (per-project review)
```

DefectDojo is for ongoing finding management. Sunshine is for point-in-time SBOM review. They don't compete; they complement.

## Strategic read

1. **DefectDojo's modular reorganization is significant.** If you're building on DefectDojo today, you may be hitting the monolith — many of the painful integrations live in `dojo/models.py`. The new modular pattern (when complete) will make customization much easier. *If you're choosing between deploying community vs. paying for Pro*, evaluate now while the OSS version is being actively modernized.
2. **Sunshine is the early sign of "SBOM tooling is becoming an ecosystem."** CycloneDX has visualization (Sunshine), VEX support coming in CycloneDX 2.0, license expressions, AI-BOM extensions. The format is winning. Expect more Sunshine-shaped focused tools — for compliance reports, for license risk, for upgrade-path analysis.
3. **EPSS + KEV are the right prioritization signals for 2026.** Most teams still triage by CVSS, which is a measure of theoretical severity. EPSS is empirical exploit probability; KEV is "we know this is being exploited right now." Sunshine bakes both in. If your DefectDojo workflow doesn't yet enrich findings with EPSS, that's the next operational upgrade.
4. **The two together encode the operational pattern that's emerging:** centralized vuln management (DefectDojo) + focused, point-of-use visualization (Sunshine). Neither alone is sufficient.
