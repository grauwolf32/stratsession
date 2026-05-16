# Perimeter security source mirrors

Git submodules of **recent (2024-2026)** OSS tools for perimeter security: modern DAST, API discovery + testing, AI-assisted templated scanners, and external recon. Selection biased toward tools first released in this window or with major rewrites / new capabilities in 2025-2026.

Mature tools (OWASP ZAP, OWASP Amass, WAF-A-MoLE, etc.) are intentionally **excluded** even when still maintained — they're documented in the [conferences](../../conferences/) and [reports](../../reports/) files but the focus here is what's *new*.

## Layout

### Modern DAST / web pentest
| Path | Upstream | Why recent |
|---|---|---|
| [`caido/`](./caido) | https://github.com/caido/caido | Rust Burp-alternative; very actively developed 2024-2026; sleek UX |

### Templated scanners + AI template generation
| Path | Upstream | Why recent |
|---|---|---|
| [`nuclei/`](./nuclei) | https://github.com/projectdiscovery/nuclei | v3.8.0 (April 2026) added AI template generation via `-ai` flag, XSS reflection-context analyzer, honeypot detector |
| [`nuclei-templates/`](./nuclei-templates) | https://github.com/projectdiscovery/nuclei-templates | 12,000+ active templates; v10.4.3 includes 2026 CVEs (ProFTPD, ActiveMQ, Fortinet FortiSandbox) |
| [`nuclei-ai-extension/`](./nuclei-ai-extension) | https://github.com/projectdiscovery/nuclei-ai-extension | 2026 browser extension for rapid template generation from natural language |
| [`nuclei-templates-ai/`](./nuclei-templates-ai) | https://github.com/projectdiscovery/nuclei-templates-ai | 2026 repository of AI-generated Nuclei templates for CVEs lacking community templates |

### Modern recon / external attack surface
| Path | Upstream | Why recent |
|---|---|---|
| [`katana/`](./katana) | https://github.com/projectdiscovery/katana | Modern Go crawler; what Vespasian uses internally for SPA crawling |
| [`httpx/`](./httpx) | https://github.com/projectdiscovery/httpx | Modern HTTP probe + tech fingerprint; actively developed |
| [`subfinder/`](./subfinder) | https://github.com/projectdiscovery/subfinder | Modern passive subdomain enumeration; v2.14 active |
| [`naabu/`](./naabu) | https://github.com/projectdiscovery/naabu | Modern Go port scanner; v2.3 active 2025-2026 |
| [`uncover/`](./uncover) | https://github.com/projectdiscovery/uncover | Search-engine-driven recon (Shodan / Censys / Fofa / Quake / Hunter) — recent addition to PD suite |

### Modern credential testing
| Path | Upstream | Why recent |
|---|---|---|
| [`brutus/`](./brutus) | https://github.com/praetorian-inc/brutus | Praetorian's Go-native multi-protocol credential validator (24 protocols, embedded SSH bad keys, RDP sticky-keys MITRE T1546.008 chain, IronRDP-via-WASM, `naabu | nerva | brutus` pipeline). Hydra successor. **(new 2026)** |

### Recent API security stack
| Path | Upstream | Why recent |
|---|---|---|
| [`akto/`](./akto) | https://github.com/akto-api-security/akto | MIT-licensed API security platform; 1000+ test templates; April 2026 release added MCP/AI agent guardrails |
| [`schemathesis/`](./schemathesis) | https://github.com/schemathesis/schemathesis | v4.17 (April 2026); property-based OpenAPI/GraphQL fuzzer; adopters: Spotify, WordPress, JetBrains, Red Hat |
| [`restler-fuzzer/`](./restler-fuzzer) | https://github.com/microsoft/restler-fuzzer | Microsoft Research stateful REST fuzzer; active 2025-2026; RAFT platform archived in favor of this |
| [`cherrybomb/`](./cherrybomb) | https://github.com/blst-security/cherrybomb | Rust CLI; audits OpenAPI specs themselves for design flaws |
| [`crapi/`](./crapi) | https://github.com/OWASP/crAPI | OWASP intentionally-vulnerable API training target; ongoing updates aligned with OWASP API Top 10 |

## How they compose for a 2026 perimeter workflow

```
External attack surface mapping
└─ subfinder + httpx + uncover (search-engine-driven discovery)
    └─ naabu (port scan)
        └─ katana (crawl)
            ├─ nuclei + nuclei-templates (templated CVE / misconfig)
            ├─ nuclei-ai-extension (generate templates for new findings live)
            └─ caido (manual interactive web pentest)
                └─ Vespasian [in ../appsec/] (capture → OpenAPI spec)
                    ├─ akto (API discovery + 1000+ tests)
                    ├─ cherrybomb (spec audit)
                    ├─ schemathesis (property-based fuzzing)
                    ├─ restler-fuzzer (stateful chains)
                    └─ Hadrian [in ../appsec/] (authZ testing)
                        └─ crapi (training target — start here)
```

## Recent-tools rationale

Several mature tools are **explicitly excluded** because they don't fit the "recent" focus:

- **OWASP ZAP** — 20+ years old; still maintained but architecturally legacy.
- **OWASP Amass** — mature; OWASP project but multi-year.
- **WAF-A-MoLE / WAFNinja** — 2020-2022 vintage; WAF testing now consolidating around WAFFLED-research-class techniques.
- **Awesome-WAF** — reference compilation, not a tool.
- **w3af / Arachni / Skipfish** — dormant.

Cross-list with other folders:

- **Coraza** + **OWASP CRS** — defensive WAF engine + ruleset, both in [`../appsec/`](../appsec/).
- **Vespasian** + **Hadrian** — API discovery + authZ testing, both in [`../appsec/`](../appsec/) (cross-listed as Praetorian's complementary pair).
- **Nettacker** — OWASP DAST/network scanner in [`../appsec/`](../appsec/).
- **Trivy** + **DefectDojo** — scanning + vuln mgmt in [`../appsec/`](../appsec/).

## Common operations

```bash
# clone everything after fresh checkout
git submodule update --init --recursive

# fetch latest upstream on a specific submodule
git submodule update --remote sources/perimeter/nuclei

# remove a submodule cleanly
git submodule deinit sources/perimeter/<name>
git rm sources/perimeter/<name>
rm -rf .git/modules/sources/perimeter/<name>
```

## Other recent tools worth knowing about (not mirrored here)

If you want any of these added as well, ask — pattern is identical:

- **APIClarity** (CNCF, `openclarity/apiclarity`) — API observability/security in K8s service meshes.
- **Caido CLI** + **Caido Plugins** — newer Caido satellite repos for headless / CI use.
- **CDNCheck** (`projectdiscovery/cdncheck`) — recent ProjectDiscovery tool for CDN detection.
- **Chaos client** (`projectdiscovery/chaos-client`) — recent passive recon data.
- **mapcidr** (`projectdiscovery/mapcidr`) — recent CIDR utility.
- **Notify** (`projectdiscovery/notify`) — pipeline notification utility, complements the recon chain.
- **Snyk Agent Scan** (`snyk/agent-scan`) — agent security scanner, more relevant to AI-stack perimeter than API perimeter; could move to a new `sources/ai-security/` folder.

The 15 in this folder are the **highest-ROI recent tools** for a perimeter security program staffed by 1-3 engineers.
