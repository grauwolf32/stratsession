# Security Research Blogs — Curated Index

**Companion to the [conferences report](../README.md)** · scope: AppSec, offensive/red team, cloud/container · window: roughly past 12 months

Blogs supply the *between-conference* signal. Conferences give you 4-month-spaced snapshots; the blogs are how the same researchers ship the in-between work (vuln disclosures, tool releases, technique deep-dives). This index groups ~27 sources into seven categories with per-source notes.

Per-source notes: [`blogs/`](./).

---

## Top-level themes across blog output (May 2025 → May 2026)

1. **AI-assisted vuln research went from prototype to weekly news.** Trail of Bits says AI-augmented auditors are finding **200 bugs/week** on the right engagements. Anthropic's "Mythos" model dominated tl;dr sec issues through Spring 2026 with claims of thousands of vulnerabilities found. GitHub shipped the **Security Lab Taskflow Agent** as an OSS framework for AI-assisted vuln triage. Doyensec, Praetorian, and SpecterOps all published AI-pipeline posts.
2. **The supply chain has been actively under attack the whole year.** Watch the JFrog, Snyk, Datadog, Aqua, and Sysdig output: **axios npm compromise** (March 2026, attributed to Sapphire Sleet / DPRK), **Shai-Hulud worm return** (25,000+ repos), **TeamPCP** spreading across PyPI → Trivy → Bitwarden CLI, **xinference / langflow / marimo / LiteLLM** all compromised. *Dependency cooldowns* and *package-namespace pinning* moved from "nice to have" to mainstream practice.
3. **K8s and cloud RCEs keep landing at scale.** Wiz disclosed multiple kernel LPEs (**Dirty Frag**, **Copy Fail CVE-2026-31431**), Sysdig and Horizon3 documented **K8s nodes/proxy → RCE**, **Ingress-NGINX retirement**, and **Langflow/Marimo** OSS RCEs.
4. **Identity attack-path management consolidated.** SpecterOps published the *Trends in Identity Attack Path Management 2026* report, **MSSQLHound moved to Go**, **Vercel breach** post-mortems hit, **NTLM reflection sequel (CVE-2025-33073)** got multi-vendor coverage.
5. **Enterprise N-day exploitation is industrialized.** Watchtowr's drumbeat: cPanel/WHM auth bypass, Progress ShareFile pre-auth RCE, Citrix NetScaler memory overreads, GNU inetutils Telnetd RCE, BMC FootPrints, Juniper Junos, SolarWinds Web Help Desk, Ivanti EPMM, SmarterTools — and that's just Q1 2026.
6. **Web research is going meta.** PortSwigger's *Top 10 Web Hacking Techniques of 2025* + Orange Tsai's *Confusion Attacks* series + Synacktiv's NTLM reflection bypass posts show the trend toward *parser-differential / protocol-misalignment* attacks (Splitting the Email Atom, WorstFit ANSI transformations).
7. **Mobile-OS in-the-wild exploits are still publishing.** Project Zero's three-part Pixel 9 0-click chain, plus their Android DNG analysis and macOS audio daemon part-II, are the canonical reference set for current mobile attack surface.

---

## Top-pick sources by use-case

### If you have **one hour a week** for security research reading

1. **tl;dr sec** newsletter (Clint Gibler) — best aggregator. Weekly.
2. **Trail of Bits Blog** — best tool-releases-per-paragraph density of any vendor.
3. **Project Zero** — irregular cadence; subscribe and read on publish.
4. **Watchtowr Labs** — best signal on enterprise N-days being actively weaponized.
5. **tl;dr sec issue archives** are themselves curation; let them filter the rest.

### If you're an **AppSec / SAST lead**

- Semgrep blog (rules, Custom Workflows, Autofix)
- GitHub blog + Security Lab (CodeQL detections, Taskflow Agent)
- Snyk Research (supply chain, dependency cooldowns)
- Trail of Bits (Testing Handbook, mutation testing tools)
- Doyensec (deep AppSec posts, less frequent but high quality)

### If you run **cloud or Kubernetes** security

- Wiz Research (highest cadence; kernel LPEs, cloud CVEs)
- Aqua Nautilus + Sysdig TRT (runtime / cloud-native threats, K8s deep-dives)
- Datadog Security Labs (detection engineering + AWS / GCP)
- Google Cloud Identity & Security blog (vendor side)

### If you're a **red teamer / offensive consultant**

- SpecterOps (AD / attack-path management; the canonical source)
- Trail of Bits + Praetorian (tooling-heavy)
- NetSPI (Azure / Salesforce / specific app pentest)
- Synacktiv (European; Windows / Kerberos / Active Directory deep-dives)
- Watchtowr / Assetnote / Horizon3 (enterprise N-days)
- Orange Tsai (web parser/protocol attacks — irregular but landmark)

### If you do **vuln research / exploit dev**

- Project Zero (Google)
- ZDI Blog (Pwn2Own + monthly Patch Tuesday review)
- Synacktiv
- Binarly (firmware/UEFI specialist)
- Microsoft Security blog (for agent-framework RCE class of disclosures)

---

## Per-source notes (organized by category)

| File | Sources covered |
|---|---|
| [offensive-vendors.md](./offensive-vendors.md) | Trail of Bits, NCC Group, Praetorian, NetSPI, Doyensec, SpecterOps, Synacktiv |
| [attack-surface.md](./attack-surface.md) | Watchtowr Labs, Assetnote, Horizon3, Orange Tsai |
| [web-research.md](./web-research.md) | PortSwigger Research |
| [cloud-native.md](./cloud-native.md) | Wiz Research, Aqua Nautilus, Sysdig TRT, Datadog Security Labs, Google Cloud Security blog |
| [supply-chain.md](./supply-chain.md) | JFrog Security Research, Snyk Research, Semgrep blog, GitHub blog / Security Lab, Binarly |
| [vendor-research.md](./vendor-research.md) | Project Zero, Microsoft Security / MSRC, Mandiant / Google Threat Intel, ZDI |
| [newsletters.md](./newsletters.md) | tl;dr sec, Risky Business |
| [oss-usage-case-studies.md](./oss-usage-case-studies.md) | Practitioner posts about *using* OSS security tools — adoption stories, scaling guidance, OSS-vs-commercial decisions |

---

## Recurring tools / projects to keep on the radar

Pulled from the blog corpus — these are the OSS tools the research community is **actively talking about**, regardless of which conference released them:

- **CodeQL** + **Taskflow Agent** (GitHub) — AI-assisted vuln triage framework, OSS.
- **Trail of Bits Buttercup** + **Trailmark** (code-to-graph) + **CoBRA** (MBA deobfuscation) + **mquire** (Linux memory forensics) + **MuTON/mewt** (mutation testing).
- **Praetorian Vespasian** (API endpoint discovery) + **Hadrian** (API authZ tester) + **Julius** (AI/cloud recon).
- **SpecterOps MSSQLHound** (Go) + BloodHound ecosystem.
- **NetSPI MicroBurst** + **ForceHound** (Salesforce attack-path).
- **OWASP Trivy MCP Server** (Aqua) — Trivy as MCP tool callable from agents.
- **Doyensec maSSO** (malicious IdP for OIDC/SAML testing) + **SafeUpdater** (Electron auto-updater reference design).
- **Synacktiv Pike** (LLM Linux-trace generator for debugging/IR).
- **Wiz Akamai integration** (edge → runtime visibility in Security Graph).

---

## Caveats

- This index covers **what each blog has been publishing**, not exhaustive single-post analysis. Per-source files have the specific post titles.
- Several sites timed out or returned errors during research (NCC Group articles index, MSRC blog, GitHub Security Lab tag page). Where I have only press / Google-search coverage, the per-source file flags it explicitly.
- Blog post titles and dates may have minor inconsistencies depending on extraction source — verify directly before citing in deliverables.
