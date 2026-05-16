# Recent Open-Source Security Tools & Approaches

**Strategy-session brief — May 2025 → May 2026** (last updated May 16, 2026)

Curated index of open-source tools, frameworks, and approaches surfaced at the major security conferences over the past 12 months. Scope: **AppSec (SAST / SCA / fuzzing / secure SDLC)**, **offensive / red team / pentest**, and **cloud / container / Kubernetes**. AI-security items are included only where they overlap those areas (e.g. LLM-assisted fuzzing, agent red-teaming frameworks used in pentest workflows).

Each item below is a one-paragraph entry. Per-conference notes live under [`conferences/`](./conferences/).

---

## Big-picture themes for the year

1. **AI-assisted vulnerability discovery moved from demo to delivery.** DARPA's AI Cyber Challenge (AIxCC) finals at DEF CON 33 awarded $8.5M, and the seven finalist Cyber Reasoning Systems — including Team Atlanta (1st, $4M) and Trail of Bits' **Buttercup** (2nd, $3M) — were **all released under OSI-approved licenses**. They are the first end-to-end open-source vuln-discovery-and-patching systems usable from a developer laptop. 18 real (non-synthetic) bugs were disclosed during finals.
2. **The "agentic security" wave hit both red and blue.** Promptfoo, GARAK (NVIDIA), PyRIT (Microsoft), Mindgard, and DeepTeam crystallized as the de-facto stack for LLM red-teaming, and tooling for *agent abuse* (Bedrock Agent takeover, Copilot prompt injection, MCP-server interception) was the most-discussed novel attack class at BH USA / DEF CON / fwd:cloudsec.
3. **Kubernetes security split into two layers.** *Detection* converged around CNCF projects (Falco + StratoShark forensics, Tetragon eBPF, Tracee), while *configuration / posture* fragmented across CEL-based scanners (**Spotter**), entitlement analyzers (**KIEMPossible**), and admission engines (**Kyverno**, **Kubewarden**) — Kyverno shipped five new policy resource types in 2025.
4. **Supply chain went baseline.** SLSA 1.1, GUAC 0.12, Sigstore "supply chain day", OWASP CycloneDX 2.0 preview + the new **Sunshine** SBOM visualizer, and CRA enforcement reset expectations: SBOM + signed provenance is no longer "leading-edge", it is the floor.
5. **C2 frameworks consolidated; evasion specialized.** **Empire 6.0** (Go agents, marketplace), **C4** (WASM cross-OS plugins), **Beaconator**, **Messenger** (tunneling), **WarHead** (Atom Tables abuse), **BOAZ** (multi-layer EDR evasion) — the offensive tooling market has matured into composable, language-agnostic stacks.
6. **Hardware / firmware / supply-chain attacks dominated the academic and offensive cons.** ReVault (Dell ControlVault3 on 100+ models, Hexacon), EntrySign (custom x86 microcode, OffensiveCon), Cypherock X1, NVIDIA CUDA driver 0-days, Apple SEP teardown.
7. **CI/CD pipeline compromise became a tier-1 risk after TeamPCP (March 2026).** A single actor chained GitHub Actions workflow injection to ship malicious updates through **Trivy, LiteLLM, KICS, Telnyx**, and dozens of npm packages. The OSS response shipped within three months: **SmokedMeat** (red-team framework for build pipelines, Boost Security Labs), **Plumber** (GitLab + GitHub CI/CD compliance scanner), **Brutus** (post-compromise credential validator, Praetorian). Companion training environment: **Whooli** — the first deliberately-vulnerable GitHub org.
8. **OSS forensics removed the "external dependency" requirement.** **CERT UEFI Parser** (CMU/SEI, NDA-free UEFI / installer / PE parsing built on Construct) and **mquire** (Trail of Bits, Linux memory forensics without external debug symbols via kernel-embedded BTF + Kallsyms) both ship in 2026. They attack the same architectural pain point — needing data you can't carry inside the artifact you're analyzing — at different layers of the stack.
9. **OSS defensive ops caught up with offensive.** **Little Snitch for Linux** (Objective Development's eBPF + Rust per-process firewall, GPL-2.0 OSS components) closes the per-host firewall gap. **Allama** (AGPL-3.0 SOAR with visual workflow builder + LLM agents on Temporal) closes the OSS SOAR gap. **Betterleaks** (drop-in Gitleaks successor by the original author, CEL filters + BPE naturalness scoring) closes the entropy-based-FP gap in secret scanning. **cloud-audit** (MIT, AWS-only opinionated scanner with attack-chain correlation + IAM escalation graph + what-if simulator) closes the "PMapper is dead" gap.

---

## Tools by theme — top picks

### Kubernetes / container security
- **Spotter** — universal Kubernetes security scanner using CEL-based rules across manifests + live clusters (OWASP K8s Top 10, CIS, NSA/CISA). DEF CON 33 Cloud Village & Demo Labs. → `madhuakula/spotter`
- **KIEMPossible** — Kubernetes Infrastructure Entitlement Management; permissions visibility + actual usage. DEF CON 33 Cloud Village (Palo Alto). → `PaloAltoNetworks/KIEMPossible`
- **Kyverno** — five new policy resource types in 2025 (ValidatingPolicy, ImageValidatingPolicy, MutatingPolicy, GeneratingPolicy, DeletingPolicy). KubeCon NA 2025.
- **Kubewarden** — admission controller now uniting Rego, CEL, and Wasm policies under one engine; group-scoped enforcement. KubeCon NA 2025.
- **Copacetic** — patches container image vulnerabilities in-place (no rebuild) using vulnerability scan output. CNCF / KubeCon NA 2025.
- **Falco + StratoShark** — Falco-triggered Wireshark-style syscall capture for forensic-grade IR. KubeCon NA 2025.
- **HoneyBee** — auto-generates intentionally-insecure Dockerfiles + Compose manifests modeling real-world misconfigs. DEF CON 33 Cloud Village. → `yaaras/honeybee`
- **DockSec** — Docker-image security analysis. OWASP Global AppSec USA 2025.

### Cloud (AWS / Azure / GCP / multi-cloud)
- **ATEAM** — Azure Tenant Enumeration and Attribution Module. DEF CON 33 Cloud Village (Karl Fosaaen + Thomas Elling, NetSPI).
- **AzDevRecon** — Azure DevOps enumeration (web UI). DEF CON 33 Cloud Village.
- **Azure AppHunter** — Azure service-principal permission scanner. DEF CON 33 Cloud Village.
- **SquarePhish 2.0** — QR-code → Entra ID token phishing toolkit. DEF CON 33 Cloud Village.
- **TencentGoat** — deliberately-vulnerable Tencent Cloud lab. DEF CON 33 Cloud Village.
- **EntraGoat** — deliberately-vulnerable Entra ID environment. DEF CON 33 Demo Labs.
- **SAMLSmith** — SAML response forging (AD FS + SaaS), red-team usage. DEF CON 33 Demo Labs. → `semperis/samlsmith`
- **OAuthSeeker** — OAuth phishing simulation for Azure/M365 red-team ops. DEF CON 33 Demo Labs. → `praetorian-inc/oauthseeker`
- **CloudFox / CloudFoxable / BadPods / IAMVulnerable** — Seth Art's cloud-pentest toolset, repeatedly featured at fwd:cloudsec NA 2025.

### Application security / fuzzing / SAST
- **Buttercup** — Trail of Bits' Cyber Reasoning System; LLM-driven fuzzing + auto-patching; runs on a developer laptop. AIxCC 2nd place, $3M, fully OSS. → `trailofbits/buttercup`
- **Atlantis (Team Atlanta CRS)** — AIxCC 1st-place CRS, OSS; engineers from Georgia Tech / KAIST / POSTECH / Samsung Research.
- **PatchLeaks** — locates vulnerable code in patches via context-aware analysis (no regex rules). DEF CON 33 Demo Labs. → `hatlesswizard/patchleaks`
- **PyIntruder** — CLI-native customizable web fuzzer. DEF CON 33 AppSec Village.
- **SeVa (Secret Validator)** — secrets-prioritization framework. DEF CON 33 AppSec Village.
- **Flowlyt** — GitHub Actions CI/CD security analyzer. DEF CON 33 AppSec Village.
- **Sunshine** — OWASP CycloneDX SBOM visualization tool. OWASP Global AppSec EU 2025.
- **OWASP DefectDojo** — vulnerability management platform; major 2025 release cycle. OWASP Global AppSec USA 2025.
- **OWASP CRS / Coraza / ModSecurity** — open WAF stack got a dedicated track at OWASP EU; Coraza roadmap update and CRS next-gen rule language preview at OWASP USA 2025.
- **OWASP Nettacker** — automated network/web vulnerability scanner — 2025 updates featured at OWASP USA 2025.

### Fuzzing research (academic — code released)
- **IDFuzz** — intelligent input mutation for directed fuzzing; complements AFL++/Fuzztruction. USENIX Security '25.
- **G²FUZZ** — outperforms AFL++/Fuzztruction/FormatFuzzer; 10 unique real-world bugs (3 CVE-confirmed). USENIX Security '25.
- **Lyso** — multi-target, multi-step directed greybox fuzzer for verifying static-analysis warnings. USENIX Security '25.
- **MBFuzzer** — multi-party MQTT broker protocol fuzzer. USENIX Security '25.
- **GenHuzz** — generative hardware fuzzer; treats fuzzing as policy optimization. USENIX Security '25.
- **DUMPLING** — differential JS-engine fuzzer; 8 new V8 bugs. NDSS 2026.
- **Fuzzilicon** — post-silicon microcode-guided x86 CPU fuzzer. NDSS 2026.
- **IoTBec** — LLM-driven firmware fuzzing with signature-based recurring-vuln detection. NDSS 2026.

### CI/CD pipeline security (offensive + defensive + credential)
- **SmokedMeat** — first OSS red-team framework purpose-built for CI/CD pipelines; full kill-chain (recon via embedded `poutine` SAST → 5 delivery methods incl. LOTP + cache poisoning → `/proc` runner memory secret scrape → OIDC cloud pivots → persistent attack graph). Ships with **Whooli** (the first deliberately-vulnerable GitHub org). AGPL-3.0. → `boostsecurityio/smokedmeat`
- **Plumber** — GitLab-first (v0.3.0 adds GitHub Actions) CI/CD compliance scanner. One Rego engine, two provider IRs, emits Pipeline Bill of Materials (PBOM) + CycloneDX SBOM. SLSA L3 attested. MPL-2.0. → `getplumber/plumber`
- **Brutus** — Praetorian's Go-native multi-protocol credential validator (24 protocols, embedded SSH bad-key collection, RDP sticky-keys MITRE T1546.008 detection + exploitation chain, IronRDP-via-WASM, `naabu | nerva | brutus` pipeline). Hydra successor. → `praetorian-inc/brutus`

### Cloud posture & attack-chain
- **cloud-audit** — opinionated AWS-only scanner (94 checks / 23 services). Attack-chain correlation (31 rules), IAM privilege escalation graph (61 methods, the open-source PMapper replacement), what-if simulator, AI-SPM checks (Bedrock + SageMaker), MCP server, breach-cost estimates, 6 compliance frameworks. MIT. → `gebalamariusz/cloud-audit`

### Firmware & memory forensics (no external symbols / SDKs)
- **CERT UEFI Parser** — CMU/SEI CERT's NDA-free UEFI ROM / installer / PE parser. Built on Construct; extensible to proprietary vendor formats; emits ASCII / JSON / SBOM-shaped JSON / Qt GUI. → `cmu-sei/cert-uefi-parser` + `cmu-sei/cert-uefi-support`
- **mquire** — Trail of Bits' Rust DFIR tool. Analyzes Linux memory snapshots **without external debug symbols**, using kernel-embedded BTF + Kallsyms. Interactive SQL shell over kernel data structures; page-cache file recovery via `.dump`; rootkit detection via multi-source task discovery. Apache-2.0. → `trailofbits/mquire`

### Defensive ops (host firewall + SOAR + secret scanning)
- **Little Snitch for Linux** (OSS components) — Objective Development's official Linux port; eBPF kernel programs + Rust common crate + JavaScript web UI. GPL-2.0. Headless / remote-browser-monitorable. Full product also includes proprietary userspace. → `obdev/littlesnitch-linux`
- **Allama** — open-source SOAR with visual workflow builder, autonomous LLM agents (PydanticAI + LiteLLM with OpenAI / Anthropic / Azure / Ollama), Temporal-backed durable execution, WebAssembly sandbox for custom Python, 80+ integrations, multi-tenant + SSO. AGPL-3.0. → `digitranslab/allama`
- **Betterleaks** — drop-in successor to Gitleaks by the original author (Zach Rice, sponsored by Aikido). CEL filters + per-rule HTTP validation + **BPE-based naturalness scoring** (replaces Shannon entropy for natural-language false-positive filtering). → `betterleaks/betterleaks`

### Offensive / red team frameworks
- **Empire 6.0** — Go-agent rewrite + module marketplace. DEF CON 33 Demo Labs. → `BC-SECURITY/Empire`
- **C4** — modular WASM-powered C2 supporting multi-language implants. DEF CON 33 Demo Labs. → `scottctaylor12/c4`
- **Beaconator** — unified listener / payload manager — "Swiss army knife for evasive C2". DEF CON 33 Demo Labs.
- **GlytchC2** — Twitch-livestream-as-C2-channel covert tooling. DEF CON 33 Demo Labs.
- **BOAZ** — multi-layered AV/EDR evasion engineering (threadless process injection primitives). DEF CON 33 Demo Labs.
- **WarHead** — Windows Atom Tables abuse for stealth payload execution. DEF CON 33 Demo Labs.
- **Metasploit (2025 updates)** — SMB relaying, AD CS attacks, SCCM exploitation workflows. DEF CON 33 Demo Labs.
- **Messenger** — local / reverse / dynamic forwarding tunneling toolkit. DEF CON 33 Demo Labs.
- **Blackdagger** — DAG-based DevSecOps + red-team automation (declarative YAML). DEF CON 33 Demo Labs.
- **AIMaL** — AI-assisted malware mutation framework for red-team simulation. DEF CON 33 Demo Labs.

### LLM / AI red-team & agent abuse (focused list — relevance to AppSec/red-team)
- **Promptfoo** — heavily featured at DEF CON 33; LLM app / MCP / agent vuln scanner; 100K+ devs.
- **GARAK** (NVIDIA), **PyRIT** (Microsoft), **DeepTeam** — converging stack for LLM red-team.
- **promptmap2** — automated prompt-injection scanner for custom LLM apps. DEF CON 33 Demo Labs. → `utkusen/promptmap`
- **MPIT (Matrix Prompt Injection Tool)** — genetic-algorithm payload optimization. DEF CON 33 Demo Labs.
- **mcp-snitch** — intercepts MCP-server traffic for analysis + audit. DEF CON 33 Cloud Village.
- **AI agent attack research** — Bedrock Agent prompt-template takeover, Microsoft Copilot AgentFlayer 0-clicks, Double Agents on AI agent platforms (fwd:cloudsec + BH USA 2025).

### Detection / DFIR (relevant to offensive validation + cloud forensics)
- **Garuda** — PowerShell framework unifying Sysmon-event hunting with filters + time-based noise reduction. DEF CON 33 Demo Labs. → `monnappa22/garuda-framework`
- **FLARE-VM** — Mandiant's reversing-VM provisioner; ongoing 2025 release cycle. DEF CON 33 Demo Labs.
- **rev.ng** — open-source binary decompiler with LLM-assisted function naming. DEF CON 33 Demo Labs.
- **Lex Sleuther** — script-language identifier (CrowdStrike). DEF CON 33 Demo Labs.

### Recon / OSINT
- **Robin** — AI-powered dark-web OSINT (multi-engine search + LLM summarization). DEF CON 33 Demo Labs + Recon Village.
- **Amass 2025** — enhanced legal-entity-based recon + RDAP-based network discovery. DEF CON 33 Recon Village.
- **TheTimeMachine** — Wayback-based historical-endpoint mining for bug-bounty. DEF CON 33 Demo Labs.

### Hardware / firmware / mobile (exploitation research with public deliverables)
- **ReVault attack chain** — full compromise of Dell ControlVault3 secure SoC across 100+ laptop models (Hexacon 2025).
- **Cypherock X1 buffer overflow** — hardware wallet USB-packet-parser vuln (Hexacon 2025).
- **EntrySign** — custom x86 microcode execution beyond ring 0 + SMM (OffensiveCon 2025).
- **CUDA driver 0-days** — fuzz-discovered NVIDIA driver bugs enabling container escape on multi-tenant GPU clouds (Hexacon 2025).
- **BaseBridge** — extension to the FirmWire baseband emulator covering MediaTek RCE research (OffensiveCon 2025).
- **Apple SEP 2025 teardown** — public reference on PAC + Trusted Boot Monitor on current Secure Enclave (Hexacon 2025).

---

## Per-conference notes

| Conference | Dates | Notes |
|---|---|---|
| [DEF CON 33](./conferences/defcon-33.md) | Aug 7-10, 2025 | Largest tool-release surface; AIxCC finals; Demo Labs ≈ 40 tools |
| [Black Hat USA 2025](./conferences/black-hat-usa-2025.md) | Aug 2-7, 2025 | 100+ Briefings, 115+ Arsenal demos; AI agent vuln chains |
| [USENIX Security '25](./conferences/usenix-ndss-2025-2026.md) | Aug 13-15, 2025 | Fuzzing papers w/ released code |
| [Hexacon 2025](./conferences/hexacon-2025.md) | Oct 6-12, 2025 | 15-talk single-track exploit conf; Pwn2Own follow-ups |
| [OWASP Global AppSec USA](./conferences/owasp-appsec-usa-2025.md) | Nov 3-7, 2025 | DC; SAMM, DefectDojo, Nettacker, CRS next-gen |
| [KubeCon + CloudNativeCon NA](./conferences/kubecon-na-2025.md) | Nov 10-13, 2025 | Atlanta; OSS SecurityCon; Kyverno / Kubewarden / Copacetic |
| [Black Hat Europe 2025](./conferences/black-hat-europe-2025.md) | Dec 8-11, 2025 | London; 55 Arsenal demos + 6 labs |
| [NDSS 2026](./conferences/usenix-ndss-2025-2026.md) | Feb 23-27, 2026 | San Diego; FUZZING'26 workshop |
| [RSA Conference 2026](./conferences/rsa-2026.md) | Mar 23-26, 2026 | SF; agentic AI + AI agents centerpiece |
| [OffensiveCon 2025 / 2026](./conferences/offensivecon-2025-2026.md) | May 16, 2025 / May 15-16, 2026 | Berlin; exploit research, no OSS culture |
| [OWASP Global AppSec EU 2025](./conferences/owasp-appsec-eu-2025.md) | May 26-30, 2025 | Barcelona; OWASP project showcase + Open WAF day |
| [Troopers 25](./conferences/troopers-25.md) | Jun 23-27, 2025 | Heidelberg; AD / Entra ID security track |
| [fwd:cloudsec NA 2025](./conferences/fwd-cloudsec-2025.md) | Jun 2025 | Cloud-attack-and-defense; community OSS focus |

---

## How to use this report
- **For tooling roadmap decisions** — open the **[`TOOLS.md`](./TOOLS.md) catalog** — flat list with verified GitHub links, grouped by category, with standout-pick markers and a 5–7 tool POC shortlist.
- **For talent / awareness signals** — the per-conference notes show *who* the active researchers are. Names recur (Madhu Akula, Seth Art, Karl Fosaaen, Donncha Ó Cearbhaill, Trail of Bits, NetSPI, Praetorian).
- **For defensive program planning** — pair offensive items with the AIxCC CRS releases and Kyverno/Kubewarden/Falco track to think in attack→detection→remediation triplets, not isolated tools.
- **For ongoing signal between conferences** — companion index of security research blogs at [`blogs/`](./blogs/) covers ~27 sources organized into seven categories (offensive vendors, attack-surface / N-day shops, web research, cloud-native, supply chain, big-tech vendor research, newsletters).
- **For technical deep-dives** — per-class comparison reports at [`reports/`](./reports/) explore the tools mirrored under [`sources/`](./sources/) as git submodules (categories: `appsec/`, `perimeter/`, `ci-cd/`, `cloud/`, `dfir/`, `defense/`). Each report identifies what's actually novel in each tool and compares tools within the same class.

## Caveats
- A small number of items are **announcements without verified release links** (e.g. RSAC 2026 Cisco "DefenseClaw", several BH USA Arsenal items reported only in press coverage — Black Hat's own pages returned 403 on fetch). These are clearly marked in the per-conference files.
- Hexacon and OffensiveCon are **research-centric, not OSS-release-centric** — they are included for situational awareness on attack-surface trends, not for tool-by-tool adoption.
- OWASP AppSec USA 2025 schedule data was extracted from sched.com excerpts; the full talk list is on https://owaspglobalappsecusa2025.sched.com/.
- 38C3 (Dec 2024) is just outside the 12-month window and is not covered here; talks are on media.ccc.de if needed.
