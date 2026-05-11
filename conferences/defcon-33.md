# DEF CON 33

**Las Vegas Convention Center · August 7–10, 2025**

DEF CON 33 produced more *publicly released open-source tools* than any other event in this report. Three surfaces matter for tooling decisions: the **AIxCC final** (DARPA AI Cyber Challenge), **Demo Labs** (the official "we made a tool, here it is" track), and the **Villages** (AppSec, Cloud, Red Team, Recon, Blue Team).

Primary index pages:
- Demo Labs: https://defcon.org/html/defcon-33/dc-33-demolabs.html
- Villages: https://defcon.org/html/defcon-33/dc-33-villages.html
- Cloud Village: https://www.cloud-village.org/dc33
- AppSec Village: https://www.appsecvillage.com/events/dc-2025
- Recon Village: https://reconvillage.org/reconvillage-2025-defcon-33

---

## AIxCC Final (DARPA AI Cyber Challenge)

DARPA AIxCC finals on the DEF CON 33 floor were arguably the most consequential single event of the year for AppSec. **$8.5M** awarded, **18 real (non-synthetic) bugs** disclosed to upstream OSS maintainers during finals (6 in C, 12 in Java). All seven finalist Cyber Reasoning Systems are being released under OSI-approved licenses.

- **Team Atlanta CRS ("Atlantis")** — 1st place, $4M. Team: Georgia Tech / KAIST / POSTECH / Samsung Research. End-to-end LLM-orchestrated fuzz + patch.
- **Buttercup** (Trail of Bits) — 2nd place, $3M. Designed to run on a developer laptop; emphasizes cost efficiency. Blog: https://blog.trailofbits.com/2025/08/09/trail-of-bits-buttercup-wins-2nd-place-in-aixcc-challenge/
- **Theori CRS** — 3rd place, $1.5M.

> Strategic note: AIxCC is the first time vendor-quality automated vuln-discovery+patch pipelines are OSS. Worth POC-ing one (Buttercup is the most accessible) against your own internal Java/C codebases.

---

## Demo Labs (selected — full list at link above)

### Offensive C2 / red team frameworks
- **Empire 6.0** (Vincent Rose, Jake Krasnov) — Go-agent rewrite + module marketplace. `BC-SECURITY/Empire`
- **C4 — Cross Compatible Command and Control** (Scott Taylor) — modular WASM C2 plugins, multi-language implants. `scottctaylor12/c4`
- **Beaconator C2 Framework** (Mike Manrod, Ezra Woods) — unified listener / payload mgmt. `croodsolutions/beaconatorc2`
- **GlytchC2** (Anil Celik, Emre Odaman) — exfiltration over Twitch live streams. `ccelikanil/glytchc2`
- **BOAZ** (Thomas Xuan Meng) — multi-layered AV/EDR evasion with threadless process injection. `thomasxm/boaz_beta`
- **WarHead** (Vishal Thakur, David Wearing) — Windows Atom Tables abuse for stealth payload exec. `malienist/warhead`
- **AIMaL** (Endrit Shaqiri, Natyra Shaqiri) — AI-mutated malware launcher for red-team simulation. `endritshaqiri/aimal`
- **Metasploit (2025 updates)** (Spencer McIntyre, Jack Heysel) — SMB relay, AD CS, SCCM exploitation. `rapid7/metasploit-framework`
- **Messenger** (Skyler Knecht, Kevin Clark) — local / reverse / dynamic forwarding tunneling. `skylerknecht/messenger`

### AppSec / fuzzing / LLM red-team
- **PatchLeaks** (Huseyn Gadashov, Abdulla Abdullayev) — context-aware patch-diff vuln locator (no regex). `hatlesswizard/patchleaks`
- **Cryptosploit** (Matt Cheung) — framework for cryptographic attacks. `nullpsifer/cryptosploit`
- **Dyna** (Arjun Chaudhary, Ayodele Ibidapo) — automates OWASP MASTG Android security audit.
- **DVBE (Damn Vulnerable Browser Extension)** (Abhinav Khanna) — purpose-built insecure WebExtension for training. `infosecak/dvbe`
- **Angry Magpie** (Jeswin Mathai, Xian Xiang Chang) — DLP-bypass simulator via browser data-splicing. `squarex-labs/angry-magpie`
- **promptmap2** (Utku Sen) — automated prompt-injection scanner for custom LLM apps. `utkusen/promptmap`
- **MPIT** (Shota Shinogi, Sasuke Kondo, Takeshi Matsuda) — genetic-algorithm LLM prompt-injection optimizer. `Sh1n0g1/mpit`

### Cloud / Kubernetes
- **Spotter** (Madhu Akula) — Kubernetes security scanner with CEL rules; OWASP K8s Top 10, CIS, NSA/CISA coverage. `madhuakula/spotter`
- **EntraGoat** (Tomer Nahum, Jonathan Elkabas) — deliberately-vulnerable Entra ID env.
- **SAMLSmith** (Eric Woodruff, Tomer Nahum) — SAML response forging tool. `semperis/samlsmith`
- **OAuthSeeker** (Adam Crosser) — OAuth phishing simulator for Azure/M365. `praetorian-inc/oauthseeker`
- **Caldera for OT** (Devon Colmer, Tony Webber) — MITRE Caldera adversary emulation for OT protocols. `mitre/caldera-ot`
- **Blackdagger** (Mahmut Erdem Ozgen, Ata Seren) — declarative YAML DAG automation for DevSecOps + red team. `erdemozgen/blackdagger`

### Defense / DFIR / reversing
- **Garuda Threat Hunting Framework** (Monnappa K A, Sajan Shetty) — PowerShell-based Sysmon-event correlation. `monnappa22/garuda-framework`
- **FLARE-VM** (Joshua Stroschein, Elliot Chernofsky) — Mandiant's reversing-VM provisioner. `mandiant/flare-vm`
- **rev.ng** (Pietro Fezzardi, Alessandro Di Federico) — static binary decompiler with LLM function naming. `revng/revng`
- **Lex Sleuther** (Aaron James) — script-language identification via lexer + ridge regression. `crowdstrike/lex_sleuther`
- **Attack Flow & Root Cause Discovery** (Ezz Tahoun, Kevin Shi) — explainable ML mapping alerts to MITRE ATT&CK (no LLM). `ezzeldinadel/attack_flow_detector`
- **RETINA** (Cesare Pizzi) — retro-game-style malware triage UX for reverse engineers. `cecio/retina`

### Recon / OSINT
- **Robin** (Apurv Singh Gautam) — AI dark-web OSINT (multi-engine + LLM summarization). `apurvsinghgautam/robin`
- **TheTimeMachine** (Arjun Chaudhary, Anmol Sachan) — Wayback Machine historical-endpoint miner. `anmolksachan/thetimemachine`

### Networking / wireless / IoT
- **nRootTag** (Junming Chen, Qiang Zeng) — Find-My-network abuse turning arbitrary PCs into trackers. https://nroottag.github.io/
- **Tengu Marauder v2** (Lexie Thach, Munir Muhammad) — ROS2 robot for wireless pentesting w/ LoRa C2. `exmachinaparlor/tengu-marauder`

---

## AppSec Village

Focus: SAST, SCA, supply chain, CI/CD, DAST, AI-supply-chain.

- **Static Analysis Hero** (Matthias Göhring, Dustin Born) — Professional sec-code-review craft sessions.
- **r/DIY: How Do We Build Our Own Code Scanning Platform?** (Charan Akiri, Christopher Guerra) — In-house scanner architecture lessons.
- **AI Supply Chain — Generating AI SBOMs for Hugging Face Models** (Helen Oakley) — ML supply chain BOM tooling.
- **SeVa — Secrets Prioritization Framework** (Pramod Rana, Leon Denard) — Secret validation + risk ranking.
- **Breaking the CI/CD Chain — GitHub Actions Risks** (Sharon Ohayon Pshoul + co).
- **Flowlyt** (HK, kvprashant, Nandan Gupta, Arif) — CI/CD flow analyzer.
- **From Tests to Targets — DAST with Selenium + ZAProxy** (Sara Martinez Giner).
- **PyIntruder** (Sagnik Haldar, Nandan Gupta, Swarup Natukula, Arif) — CLI-native customizable web fuzzer.

---

## Cloud Village

Three days, ~25 talks; focused on AWS/Azure/GCP attack + defense + GenAI/cloud intersection.

Notable tool releases:

- **ATEAM** (Karl Fosaaen, Thomas Elling) — Azure Tenant Enumeration and Attribution Module.
- **AzDevRecon** (Raunak Parmar) — Azure DevOps enumeration (web UI).
- **Azure AppHunter** (Marios Gyftos, Nikos Vourdas) — service-principal permission scanner.
- **Spotter** (Madhu Akula) — *re-presented* at Cloud Village.
- **TencentGoat** (Muhammad Yuga Nugraha) — vulnerable Tencent Cloud lab env.
- **SquarePhish 2.0** (Nevada Romsdahl, Kam Talebzadeh) — QR-to-Entra ID token phishing.
- **HoneyBee** (Yaara Shriki, Wiz) — auto-gen insecure Docker/Compose manifests. `yaaras/honeybee`
- **KIEMPossible** (Golan Myers, Palo Alto) — Kubernetes entitlement analyzer. `PaloAltoNetworks/KIEMPossible`
- **Sketchy** (Adversis) — cross-platform behavior scanner (25+ suspicious patterns). `Adversis/sketchy`
- **mcp-snitch** (Adversis) — macOS MCP-server traffic interceptor. `Adversis/mcp-snitch`
- **Weaponizing SageMaker AI** (Shani Peled) — new OSS post-exploitation framework for SageMaker.
- **Living off the Graph** (Trevor) — PowerShell Azure recon via Microsoft Graph.

Also-notable talks without OSS releases: ECS-cape (IAM privilege hijack in ECS), whoAMI (AMI name confusion), ESXi persistence research, Azure managed-identity research.

---

## Red Team Village

- **azbridge offensive abuse** — workshop exposing Microsoft's azbridge as a covert C2 channel for lateral movement / persistence using legitimate MS infrastructure.
- **Kestrel for adversary simulation in critical infrastructure** — workshop using Kestrel hunting language inverted for offense.
- **Garuda** (cross-listed) — Sysmon event analysis framework for unified detection.

## Recon Village

- **Robin** (cross-listed) — AI dark web OSINT.
- **Amass new features** — legal-entity-based recon, RDAP-based network discovery for bottom-up infra mapping.
- **Building Local Knowledge Graphs for OSINT** (Donald Pellegrino) — `DeciSym/recon-village-2025-defcon33-decisym`.

## Packet Hacking Village

Strong AI-for-blue-team theme this year — AI for packet analysis, AI for NIDS, AI for honeypots, AI for log analysis / threat detection.

## Blue Team Village (BTV)

Tracks: IR, Forensics, Cyber Threat Hunting, Detection Engineering, OT, Insider Threat. Garuda was the headline new tool release.

---

## High-impact briefings / vulnerability disclosures from DEF CON 33 + Black Hat USA 2025 floor

These were widely reported but tool releases were limited:

- **HashiCorp Vault + CyberArk Conjur logic flaws** (Cyata research).
- **Dell ControlVault3 / "ReVault"** (Philippe Laulheret — also at Hexacon 2025).
- **AgentFlayer zero-clicks** against ChatGPT / Gemini / Copilot enterprise agents (Zenity).
- **AirPlay wormable RCE** (Oligo / various).
- **Wormable 5G baseband flaws.**
- **VisionSpace — space-mission-ending vuln chain.**

---

## Sources
- DEF CON Demo Labs index: https://defcon.org/html/defcon-33/dc-33-demolabs.html
- Cloud Village schedule: https://www.cloud-village.org/dc33
- AppSec Village: https://www.appsecvillage.com/events/dc-2025
- Recon Village talks: https://reconvillage.org/reconvillage-2025-defcon-33/talks
- AIxCC results: https://www.darpa.mil/news/2025/aixcc-results
- Buttercup write-up: https://blog.trailofbits.com/2025/08/09/trail-of-bits-buttercup-wins-2nd-place-in-aixcc-challenge/
- tl;dr sec recap of Cloud Village: https://tldrsec.com/p/tldr-sec-301
- HackerOne DEF CON 33 AI/red-team recap: https://www.hackerone.com/blog/defcon33-ai-security
