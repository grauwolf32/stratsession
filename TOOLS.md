# Promising Tools — GitHub Catalog

Flat catalog of the strongest open-source security tools surfaced in the [conferences report](./README.md) and [blogs index](./blogs/README.md). All links verified.

Scope: **AppSec / SAST / SCA / fuzzing**, **offensive / red team / pentest**, **cloud / container / Kubernetes**. AI-security items included where they overlap those scopes.

Conventions:
- **★** = standout pick in its category (highest-impact 2025–2026 release).
- **(new 2025/2026)** = first release or major rewrite in this window.

---

## 1. AI-assisted vulnerability research & auto-patching

| Tool | Repo | Notes |
|---|---|---|
| ★ Buttercup CRS (Trail of Bits) | https://github.com/trailofbits/buttercup | 2nd-place AIxCC, $3M. End-to-end LLM-driven fuzz + patch on a developer laptop. Found 28 vulns / 20 CWEs at 90% accuracy. **(new 2025)** |
| Buttercup — AIxCC final submission | https://github.com/trailofbits/afc-buttercup | Frozen-at-finals snapshot. |
| Buttercup — AIxCC semifinal | https://github.com/trailofbits/asc-buttercup | Earlier reference build. |
| ★ Seclab Taskflow Agent (GitHub Security Lab) | https://github.com/GitHubSecurityLab/seclab-taskflow-agent | YAML-driven multi-agent vuln-research framework. Found 80+ OSS flaws in production use. **(new 2026)** |
| Seclab Taskflows (companion) | https://github.com/GitHubSecurityLab/seclab-taskflows | Example YAML taskflows + custom MCP servers. |
| Trailmark (Trail of Bits) | https://github.com/trailofbits/trailmark | Source → callgraph + semantic graph; queryable from Claude skills. 17 languages. **(new 2026)** |

## 2. SAST / SCA / supply chain

| Tool | Repo | Notes |
|---|---|---|
| ★ Trivy | https://github.com/aquasecurity/trivy | The default OSS scanner: containers, K8s, IaC, repos, cloud. |
| Trivy MCP plugin | https://github.com/aquasecurity/trivy-mcp | Trivy as an MCP server — callable from Claude / VS Code / Cursor. **(new 2026)** |
| OWASP Sunshine | https://github.com/CycloneDX/Sunshine | OWASP CycloneDX SBOM visualizer; enriches with EPSS + CISA KEV. **(new 2025)** |
| OWASP CycloneDX spec | https://github.com/CycloneDX/specification | SBOM format itself (2.0 preview at OWASP USA 2025). |
| OWASP DefectDojo | https://github.com/DefectDojo/django-DefectDojo | Vulnerability management / triage platform. |
| OWASP Nettacker | https://github.com/OWASP/Nettacker | Automated network + web scanner. |
| OWASP Coraza | https://github.com/corazawaf/coraza | Go-native WAF (ModSecurity successor). |
| OWASP Core Rule Set (CRS) | https://github.com/coreruleset/coreruleset | Industry-standard WAF rule set. Next-gen rule language in progress. |
| PatchLeaks | https://github.com/hatlesswizard/patchleaks | Locates vulnerable code in patches via context-aware analysis. **(new 2025)** |
| ★ Betterleaks | https://github.com/betterleaks/betterleaks | Drop-in successor to Gitleaks by the same author (Zach Rice) + Aikido. CEL filters, BPE-based naturalness scoring, per-rule HTTP validation. **(new 2026)** |
| CERT UEFI Parser | https://github.com/cmu-sei/cert-uefi-parser | CMU/SEI CERT's NDA-free UEFI ROM / installer / PE parser. Construct-based, extensible; emits SBOM-shaped JSON. **(new 2026)** |

## 3. Fuzzing

| Tool | Repo | Notes |
|---|---|---|
| Ruzzy (Trail of Bits) | https://github.com/trailofbits/ruzzy | Coverage-guided Ruby fuzzer; now LibAFL-backed. |
| LibAFL | https://github.com/AFLplusplus/LibAFL | Modern fuzzer framework — referenced everywhere. |
| AFL++ | https://github.com/AFLplusplus/AFLplusplus | The de-facto greybox fuzzer. |
| OSS-Fuzz | https://github.com/google/oss-fuzz | Google's continuous-fuzzing service; baseline integration target. |

*USENIX '25 / NDSS '26 fuzzers (IDFuzz, G²FUZZ, Lyso, MBFuzzer, GenHuzz, DUMPLING, Fuzzilicon, IoTBec) — code release locations vary; see paper URLs in [`conferences/usenix-ndss-2025-2026.md`](./conferences/usenix-ndss-2025-2026.md).*

## 4. Kubernetes / container security

| Tool | Repo | Notes |
|---|---|---|
| ★ Spotter | https://github.com/madhuakula/spotter | CEL-based K8s scanner covering OWASP K8s Top 10, CIS, NSA/CISA. **(new 2025)** |
| ★ Kyverno | https://github.com/kyverno/kyverno | Policy-as-code engine; five new policy resource types in 2025. |
| Kubewarden | https://github.com/kubewarden/kubewarden-controller | Wasm + Rego + CEL admission controller. |
| Copacetic | https://github.com/project-copacetic/copacetic | Patch container images in place; no rebuild. **(new emphasis 2025)** |
| Open Policy Agent | https://github.com/open-policy-agent/opa | Post-1.0 perf gains in 2025. |
| Falco | https://github.com/falcosecurity/falco | CNCF-graduated runtime detection. |
| Stratoshark | https://github.com/sysdiglabs/stratoshark | Wireshark-for-syscalls; triggered by Falco for forensic captures. **(new 2025)** |
| KIEMPossible | https://github.com/PaloAltoNetworks/KIEMPossible | Kubernetes Infrastructure Entitlement Management. **(new 2025)** |
| HoneyBee | https://github.com/yaaras/honeybee | Auto-generates intentionally insecure Dockerfiles/Compose. **(new 2025)** |
| BadPods | https://github.com/BishopFox/badPods | Reference manifests for K8s privesc training. |
| Caldera for OT | https://github.com/mitre/caldera-ot | MITRE Caldera for OT-protocol adversary emulation. |

## 5. Cloud (AWS / Azure / GCP) attack & posture

| Tool | Repo | Notes |
|---|---|---|
| ★ Prowler | https://github.com/prowler-cloud/prowler | Most-deployed OSS cloud security scanner (AWS / GCP / Azure / K8s). |
| CloudFox | https://github.com/BishopFox/cloudfox | Situational awareness in AWS; finds privesc paths. |
| CloudFoxable | https://github.com/BishopFox/cloudfoxable | Vulnerable AWS env companion. |
| IAMVulnerable | https://github.com/BishopFox/IAMVulnerable | Terraform-deployed deliberately-vuln AWS IAM lab. |
| MicroBurst (NetSPI) | https://github.com/NetSPI/MicroBurst | Foundational Azure attack toolkit. |
| ★ EntraGoat (Semperis) | https://github.com/Semperis/EntraGoat | Deliberately-vulnerable Entra ID lab. **(new 2025)** |
| SAMLSmith (Semperis) | https://github.com/Semperis/samlsmith | SAML response forging for red-team ops. **(new 2025)** |
| OAuthSeeker (Praetorian) | https://github.com/praetorian-inc/oauthseeker | Azure/M365 OAuth phishing simulator. **(new 2025)** |
| maSSO (Doyensec) | https://github.com/doyensec/cloudsec-tidbits/tree/main/lab-masso | Malicious IdP for OIDC/SAML SP security testing. **(new 2026)** |
| ForceHound (NetSPI) | https://github.com/NetSPI/ForceHound | Salesforce permission graph → BloodHound CE. **(new 2026)** |
| ★ cloud-audit | https://github.com/gebalamariusz/cloud-audit | AWS-only opinionated scanner (94 checks / 23 services). Attack-chain correlation (31 rules), IAM escalation graph (61 methods + AssumeRole lateral), what-if simulator, AI-SPM checks, MCP server, breach-cost estimates. MIT. **(new 2026)** |

## 6. Identity / Active Directory / Entra

| Tool | Repo | Notes |
|---|---|---|
| ★ BloodHound (Community Edition) | https://github.com/SpecterOps/BloodHound | The canonical AD attack-path tool. |
| AzureHound | https://github.com/SpecterOps/AzureHound | Azure / Entra ID data exporter for BloodHound. |
| MSSQLHound | https://github.com/SpecterOps/MSSQLHound | MSSQL attack paths into BloodHound (Go rewrite in 2026). **(rewritten 2026)** |

## 7. C2 / red team frameworks

| Tool | Repo | Notes |
|---|---|---|
| ★ Empire 6.0 | https://github.com/BC-SECURITY/Empire | Go-agent rewrite + module marketplace. **(new 2025)** |
| Metasploit Framework | https://github.com/rapid7/metasploit-framework | 2025 updates: SMB relaying, AD CS, SCCM exploitation. |
| C4 | https://github.com/scottctaylor12/c4 | Modular WASM-powered cross-OS C2. **(new 2025)** |
| Beaconator C2 | https://github.com/croodsolutions/beaconatorc2 | Unified listener / payload management. **(new 2025)** |
| GlytchC2 | https://github.com/ccelikanil/glytchc2 | Twitch-livestream-as-C2-channel. **(new 2025)** |
| BOAZ | https://github.com/thomasxm/boaz_beta | Multi-layered AV/EDR evasion + threadless process injection. **(new 2025)** |
| WarHead | https://github.com/malienist/warhead | Windows Atom Tables abuse for stealth payload exec. **(new 2025)** |
| AIMaL | https://github.com/endritshaqiri/aimal | AI-mutated malware launcher for red-team simulation. **(new 2025)** |
| Messenger | https://github.com/skylerknecht/messenger | Tunneling toolkit (local/reverse/dynamic forwarding). **(new 2025)** |
| Blackdagger | https://github.com/erdemozgen/blackdagger | YAML DAG automation for DevSecOps + red team. **(new 2025)** |
| ★ SmokedMeat | https://github.com/boostsecurityio/smokedmeat | First OSS red-team framework purpose-built for CI/CD pipelines ("Like Metasploit, but for CI/CD"). Full kill-chain: poutine-based recon → injection/LOTP/cache-poison delivery → `/proc` runner memory scrape → OIDC cloud pivots. Ships with the Whooli deliberately-vulnerable training org. AGPL-3.0. **(new 2026)** |
| ★ Plumber | https://github.com/getplumber/plumber | GitLab-first + GitHub Actions CI/CD compliance scanner. One Rego engine, two provider IRs, emits PBOM + CycloneDX. MPL-2.0. **(new 2026)** |
| ★ Brutus | https://github.com/praetorian-inc/brutus | Praetorian's Go-native multi-protocol credential validator (24 protocols, embedded SSH bad keys, RDP sticky-keys MITRE T1546.008 detection + exploitation, IronRDP-via-WASM, `naabu | nerva | brutus` pipeline). Hydra successor. **(new 2026)** |

## 8. AppSec / web / API offensive tooling

| Tool | Repo | Notes |
|---|---|---|
| ★ Vespasian (Praetorian) | https://github.com/praetorian-inc/vespasian | API discovery + spec generation (OpenAPI/GraphQL SDL/WSDL). **(new 2026)** |
| ★ Hadrian (Praetorian) | https://github.com/praetorian-inc/hadrian | YAML-driven API authZ testing (REST / GraphQL / gRPC). **(new 2026)** |
| Julius (Praetorian) | https://github.com/praetorian-inc/julius | LLM service fingerprinter — detects 60+ AI services from IP:port. **(new 2026)** |
| Praetorian capabilities (combined) | https://github.com/praetorian-inc/capabilities | Aggregated OSS offensive capabilities (Chariot). |
| Cryptosploit | https://github.com/nullpsifer/cryptosploit | Cryptographic attack framework. **(new 2025)** |
| Angry Magpie | https://github.com/squarex-labs/angry-magpie | DLP-bypass simulator via browser data-splicing. **(new 2025)** |
| DVBE (Damn Vulnerable Browser Extension) | https://github.com/infosecak/dvbe | Vulnerable WebExtension for training. **(new 2025)** |
| SafeUpdater (Doyensec) | https://github.com/doyensec/ElectronSafeUpdater | Reference design for secure Electron auto-updates. **(new 2026)** |

## 9. LLM / AI red team & prompt-injection testing

| Tool | Repo | Notes |
|---|---|---|
| ★ Promptfoo | https://github.com/promptfoo/promptfoo | LLM app / MCP / agent vuln scanner. 100K+ devs. |
| ★ GARAK (NVIDIA) | https://github.com/NVIDIA/garak | LLM vuln scanner — data leakage, misinformation, auto-attack gen. |
| PyRIT (Microsoft) | https://github.com/Azure/PyRIT | Python Risk Identification Toolkit for AI security. |
| DeepTeam | https://github.com/confident-ai/deepteam | Framework to red-team LLMs + LLM systems. |
| promptmap2 | https://github.com/utkusen/promptmap | Automated prompt-injection scanner. **(new 2025)** |
| MPIT | https://github.com/Sh1n0g1/mpit | Genetic-algorithm prompt-injection payload optimizer. **(new 2025)** |
| Pike (Synacktiv) | https://github.com/synacktiv/pike-agent | LLM agent that analyzes Linux strace recordings via chat UI. **(new 2026)** |
| Sketchy (Adversis) | https://github.com/Adversis/sketchy | Cross-platform behavioral scanner — 25+ suspicious patterns. **(new 2025)** |
| mcp-snitch (Adversis) | https://github.com/Adversis/mcp-snitch | macOS MCP-server traffic interceptor + audit log. **(new 2025)** |

## 10. DFIR / defense / reversing

| Tool | Repo | Notes |
|---|---|---|
| FLARE-VM (Mandiant) | https://github.com/mandiant/flare-vm | Reverse-engineering Windows VM provisioner. |
| Garuda Threat Hunting Framework | https://github.com/monnappa22/garuda-framework | PowerShell-based Sysmon-event correlation. **(new 2025)** |
| rev.ng | https://github.com/revng/revng | OSS static binary decompiler with LLM-assisted function naming. |
| Lex Sleuther (CrowdStrike) | https://github.com/crowdstrike/lex_sleuther | Script-language ID via lexer + ridge regression. **(new 2025)** |
| Attack Flow Detector | https://github.com/ezzeldinadel/attack_flow_detector | Map alerts to MITRE ATT&CK using explainable ML (no LLM). **(new 2025)** |
| RETINA | https://github.com/cecio/retina | Retro-game-style malware-triage UX. **(new 2025)** |
| ★ mquire (Trail of Bits) | https://github.com/trailofbits/mquire | Zero-dependency Linux memory forensics via BTF/kallsyms. SQL shell over kernel data structures; page-cache file recovery; rootkit detection via multi-source task discovery. Apache-2.0. **(new 2026)** |
| CoBRA (Trail of Bits) | https://github.com/trailofbits/CoBRA | Mixed-Boolean-Arithmetic expression deobfuscator. **(new 2026)** |

## 10b. Defensive ops (host firewall + SOAR)

| Tool | Repo | Notes |
|---|---|---|
| ★ Little Snitch for Linux (OSS components) | https://github.com/obdev/littlesnitch-linux | Objective Development's official Linux port. eBPF kernel programs + Rust common + JS web UI. GPL-2.0 OSS portion (full product also includes proprietary userspace). **(new 2026)** |
| OpenSnitch | https://github.com/evilsocket/opensnitch | The mature fully-OSS alternative; netfilter NFQUEUE + Python daemon + Qt UI. |
| ★ Allama | https://github.com/digitranslab/allama | Open-source SOAR with visual workflow builder, autonomous LLM agents (PydanticAI + LiteLLM), Temporal durable execution, WASM sandbox for custom Python, 80+ integrations, multi-tenant + SSO. AGPL-3.0. **(new 2026)** |
| Shuffle | https://github.com/Shuffle/Shuffle | The mature OSS SOAR competitor; broader integration catalog, own workflow runtime. |
| TheHive + Cortex | https://github.com/TheHive-Project/TheHive | OSS incident-response case management + analyzer framework. Pairs well with Allama. |

## 11. Recon / OSINT

| Tool | Repo | Notes |
|---|---|---|
| Robin | https://github.com/apurvsinghgautam/robin | AI dark-web OSINT (multi-engine search + LLM summarization). **(new 2025)** |
| TheTimeMachine | https://github.com/anmolksachan/thetimemachine | Wayback Machine historical-endpoint miner. **(new 2025)** |
| Amass | https://github.com/owasp-amass/amass | Long-standing recon framework; 2025 RDAP + legal-entity recon updates. |

## 12. Hardware / wireless / IoT

| Tool | Repo | Notes |
|---|---|---|
| Tengu Marauder v2 | https://github.com/exmachinaparlor/tengu-marauder | ROS2 wireless-pentest robot with LoRa C2. **(new 2025)** |

## 13. AIxCC finalists (all OSI-licensed)

The full list of the seven AIxCC final Cyber Reasoning Systems being released:

- Trail of Bits Buttercup → https://github.com/trailofbits/buttercup (2nd place, $3M)
- Team Atlanta "Atlantis" CRS — 1st place, $4M (Georgia Tech / KAIST / POSTECH / Samsung Research). Repo cluster lives under https://github.com/team-atlanta — verify exact CRS repo name before citing.
- Theori CRS — 3rd place, $1.5M.
- 4 other finalist CRSs were released or are in the process of release per DARPA's August 2025 announcement.

See https://www.darpa.mil/news/2025/aixcc-results for the canonical list as releases land.

---

## Quick "what to POC first" shortlist

If your team can only evaluate **5–7 new tools** this quarter, here are my picks across the catalog (updated May 2026 for the post-TeamPCP wave):

1. **SmokedMeat + Whooli** — set up the deliberately-vulnerable training org and run a CI/CD tabletop. Highest signal-per-hour security exercise of 2026.
2. **Plumber** — drop in as a CI/CD compliance gate on GitLab today (v0.2.x stable); evaluate v0.3.0 for GitHub Actions in parallel.
3. **Buttercup** — the most consequential OSS release of 2025; representative of AI-assisted vuln research becoming actually usable.
4. **cloud-audit** — fastest way to get an actionable AWS posture report with attack-chain ranking + reviewable Terraform/CLI remediation. Run alongside Prowler, not instead of.
5. **Betterleaks** — drop-in Gitleaks replacement; immediate FP reduction via BPE naturalness scoring. Migration is incremental.
6. **mquire** — adopt in IR / forensics workflows when external debug symbols aren't available. Big quality-of-life upgrade over Volatility for Linux memory.
7. **Brutus** — replace Hydra in your credential-validation pipelines, especially if you use `naabu` already.

Honorable mentions for theme parity:
- **Vespasian + Hadrian** — biggest 2026 OSS step forward in API attack-surface coverage.
- **Spotter + Kyverno + Copacetic** — three-piece Kubernetes posture upgrade stack.
- **Allama** — if you're shopping for OSS SOAR specifically.
- **CERT UEFI Parser** — only if firmware analysis is on your team's roadmap; otherwise file under "good to know exists."

---

## Caveats

- Three AIxCC finalist CRSs have not yet been clearly named in public press; verify each repo's release notes before integrating.
- A handful of tools listed in the conferences notes (e.g. `EntraGoat` originally said "no GitHub listed" in some recaps) are now publicly hosted — repo links above reflect the current state.
- Tools marked **(new 2025/2026)** were either first-released or had a major refactor in this window; existing well-established projects (Empire, Metasploit, BloodHound, Prowler, OPA, Falco) are included without that tag.
