# Offensive-research vendor blogs

These are the consulting/research shops that publish *original* offensive research, not just incident write-ups. Generally the highest-density technical content per post.

---

## Trail of Bits — https://blog.trailofbits.com/

**Why it matters:** Highest tool-release density of any vendor blog. Cryptography + smart-contracts + AppSec + fuzzing + AI-for-security all under one roof. Their headline 2025 stat: 375+ merged PRs across 90+ OSS projects, including Sigstore, the Rust compiler, and the `cryptography` lib.

Recent notable posts:

- **C/C++ checklist challenges, solved** (May 2026) — Linux ping inet_ntoa buffer gotcha + Windows driver registry bugs walkthroughs.
- **Extending Ruzzy with LibAFL** (April 2026) — coverage-guided fuzzing engine for Ruby code now LibAFL-backed.
- **Trailmark turns code into graphs** (April 2026) — source-code-to-security-graph engine powering eight Claude Code skills for blast-radius analysis. *Worth piloting on your own codebase*.
- **We beat Google's zero-knowledge proof of quantum cryptanalysis** (April 2026) — exploited vulns in Google's Rust zkVM.
- **Master C and C++ with our new Testing Handbook chapter** (April 2026) — checklist resource. The Testing Handbook is the most useful long-form security-review reference Trail of Bits has ever published — bookmark it for code-review onboarding.
- **What we learned about TEE security from auditing WhatsApp's Private Inference** (April 2026) — TEEs are not a magic security primitive.
- **Simplifying MBA obfuscation with CoBRA** (April 2026) — OSS Mixed-Boolean-Arithmetic deobfuscator.
- **Mutation testing for the agentic era** (April 2026) — released **MuTON** and **mewt** mutation-testing tools.
- **How we made Trail of Bits AI-native** (March 2026) — "AI-augmented auditors are finding 200 bugs a week on the right engagements." Single most useful read on operationalizing AI into a security-consulting workflow.
- **Try our new dimensional analysis Claude plugin** + **Spotting issues in DeFi with dimensional analysis** (March 2026) — LLM annotates code with dimensional types; 93% recall. Cross-applies to smart-contract auditing.
- **Six mistakes in ERC-4337 smart accounts** (March 2026) — DeFi audit patterns.
- **mquire** (February 2026) — Linux memory forensics without external dependencies / debug info.
- **Using threat modeling and prompt injection to audit Comet** (February 2026) — Perplexity Comet → Gmail-exfil prompt-injection chain.
- **Carelessness versus craftsmanship in cryptography** (February 2026) — IV reuse risks in aes-js / pyaes.
- **Celebrating our 2025 open-source contributions** (January 2026).
- **Building cryptographic agility into Sigstore** (January 2026).
- **Buttercup wins 2nd place in AIxCC Challenge** (August 2025) — see also `conferences/defcon-33.md`.

---

## NCC Group — https://www.nccgroup.com/research/

**Why it matters:** Long-running independent research shop with strong exploit-dev and crypto pedigree. The Exploit Development Group (EDG) is the canonical reference for embedded/automotive vuln research.

The article-index page consistently timed out during research, so this is sourced from NCC's annual report + threat-pulse posts:

- **Annual Cyber Security Research Report 2025** (released Feb 26, 2026) — 1100+ research days, 40 publications, **17 new or updated public tools**, 8 technical advisories, 8 public reports.
- **Monthly Threat Pulse** series (`/newsroom/ncc-group-monthly-threat-pulse-…`) — useful month-over-month ransomware-and-trend signal.
- Research themes for 2025 per the annual report: AI security (deepfake vishing, prompt injection, unsafe agentic AI, "shadow AI"), automotive exploitation, embedded device research, hypervisor security, **AI-augmented vulnerability analysis** (EDG).
- Disclosed: Cisco Secure Firewall Management Centre critical-severity RCE (Java-code-exec with root, weaponized by Interlock ransomware).

To get the per-post detail you'd typically pull from the index, hit https://www.nccgroup.com/research/research-articles/ directly in a browser — it is interactive-heavy and didn't render via WebFetch.

---

## Praetorian — https://www.praetorian.com/blog/

**Why it matters:** Strong cloud + AD + AI red-team output. Their tools are often released directly into open source.

Recent notable posts:

- **The Attack Helix: Praetorian's AI & Economic Architecture for Offensive Security** (April 2026) — framing piece on AI + compute scaling in offensive work.
- **Shadow Admins in Active Directory** (April 2026) — covert AD admin paths.
- **Bypassing LLM Supervisor Agents Through Indirect Prompt Injection** (April 2026).
- **Meet Vespasian. It Sees What Static Analysis Can't.** (April 2026) — **open-source API endpoint discovery tool** that beats conventional methods.
- **Your API Has Authorization Bugs. Hadrian Finds Them.** (March 2026) — **open-source API authZ vuln detector**.
- **Reflecting on Your Tier Model: CVE-2025-33073 and the One-Hop Problem** (March 2026) — NTLM reflection sequel analysis aimed at network segmentation defenders.
- **Which Came First: The System Prompt, or the RCE?** (March 2026) — agent-RCE chain analysis.
- **Julius v0.2.0: From 33 to 63 Probes** (March 2026) — cloud/AI service detection tool; now detects Cloud AI, Enterprise Inference, and RAG pipelines.

**Tools to look at:** Vespasian + Hadrian + Julius are the three OSS releases worth tracking from Praetorian in this window.

---

## NetSPI — https://www.netspi.com/blog/technical-blog/

**Why it matters:** Azure-specialist pentest content. Karl Fosaaen and team are arguably the highest-output Azure pentest researchers in the industry. **MicroBurst** is the foundational Azure-attack toolkit.

Recent notable posts:

- **Walking Through an Attack Path with ForceHound** + **Auditing Salesforce Permission Hierarchies with ForceHound** (April 2026) — released **ForceHound**, a Salesforce permission attack-path tool (BloodHound model applied to Salesforce). Notable as Salesforce-attack-path-management was an unfilled gap before this.
- **7 Ways to Execute Command on Azure Virtual Machines & Scale Sets** (March 2026).
- **Pipe Dreams: RCE via Quest Desktop Authority Named Pipe** (February 2026) — CVE-2025-67813 analysis.
- **Rust's Role in Embedded Security** (January 2026).
- **Decrypting VM Extension Settings with Azure WireServer** (October 2025).
- **We Know What You Did (in Azure) Last Summer** (August 2025) — also at DEF CON 33 Cloud Village.
- **Automating Azure App Services Token Decryption** (July 2025) — MicroBurst update.
- **CVE-2025-4660: Forescout SecureConnector RCE** (July 2025).
- **Detecting Authorization Flaws in Java Spring via Source Code Review** (July 2025).
- **Set Sail: RCE in SailPoint IQService** (July 2025).
- **Extracting Sensitive Information from Azure Load Testing** (July 2025).

**Tools to follow:** MicroBurst (Azure), ForceHound (Salesforce), the team's recurring Azure recon module releases.

---

## Doyensec — https://blog.doyensec.com/

**Why it matters:** Lower volume but very deep AppSec posts. Strong on auth/authZ, IdP integration, and reference-quality design documents.

Recent notable posts:

- **The Danger of Multi-SSO AWS Cognito User Pools** (May 2026) — JIT ghost identity injection, IdP identifier hijacking, federated username parsing attacks. Released **maSSO** — *malicious IdP tool* for OIDC/SAML SP testing. This is a unique capability in OSS.
- **CFITSIO Fuzzing: Memory Corruptions and a Codex-Assisted Pipeline** (April 2026) — 16 unique memory corruption bugs found in the astronomy CFITSIO library via AFL++ with LLM-assisted triage + patch generation. **Best reference write-up on hybrid fuzz+LLM workflows** in this window.
- **The MCP AuthN/Z Nightmare** (March 2026) — auth/authZ analysis of Model Context Protocol; tool poisoning, prompt injection, command injection vectors; critique of Identity Assertion JWT Authorization Grant (JAG).
- **Building a Secure Electron Auto-Updater** (February 2026) — **SafeUpdater** reference design with Ed25519 + SHA-512 + immutable manifests. Reusable starting point for any team building update channels.

---

## SpecterOps — https://specterops.io/blog

**Why it matters:** BloodHound creators. The canonical source for Active Directory + Entra ID attack-path management, which is the dominant operational red-team workflow.

Recent notable posts:

- **Shift Happens** (May 2026) — two built-in command-injection bugs in Windows context menus.
- **The Accidental C2: Exploring Dev Tunnels for Remote Access** (May 2026).
- **How We Think about Red Teaming** (May 2026) — SpecterOps methodology piece; useful for vendor selection conversations.
- **Identity APM Has Gone Mainstream. The Hard Work Is Just Starting.** (April 2026) — release of *Trends in Identity Attack Path Management 2026* report (500+ security decision-makers surveyed).
- **MSSQLHound Now Available in Go** (April 2026) — rewritten in Go for cross-platform + SOCKS proxy. Drop-in upgrade for existing BloodHound users.
- **SpecterOps Selected for OpenAI's Trusted Access for Cyber Program** (April 2026) — signal that AI providers are formalizing offensive-research partnerships.
- **The Vercel Breach Explains Why Identity Attack Path Management Can't Wait** (April 2026) — non-human-identity / NHI breach analysis.
- **Into The Rainbow: Google's NTLMv1 Rainbow Tables Explained** (April 2026) — practical tradecraft for NTLMv1 cracking.

**Tools to follow:** BloodHound CE / BHE, MSSQLHound (now Go), Certify, Rubeus, SharpHound. Identity APM as a category is largely SpecterOps-shaped.

---

## Synacktiv — https://www.synacktiv.com/en/publications

**Why it matters:** Top-tier French offensive shop. Strong on Windows / AD / Kerberos, recurring Pwn2Own competitors, and a steady stream of exploit-dev write-ups.

Recent notable posts:

- **Make it Blink: Over-the-Air Exploitation of the Philips Hue Bridge** (May 2026) — RCE from the Zigbee network; Pwn2Own.
- **Bypassing Windows Authentication Reflection Mitigations - Part 1 & 2** (April 2026) — CVE-2025-33073 and the Kerberos coercion technique exploiting Unicode handling. Pair this with Praetorian's CVE-2025-33073 piece for full coverage.
- **Say hi to Pike!** (April 2026) — released **Pike**, an LLM agent that generates and analyzes Linux execution traces for debugging and malware ID.
- **Hooking Windows Named Pipes** (April 2026) — IPC exploitation for unpriv → elevated escalation.
- **Kubernetes Forensics 1/3: What the Container?** (March 2026) — start of a forensics series.
- **Exploring Cross-Domain & Cross-Forest RBCD** (March 2026) — RBCD attack across AD forests.
- **Deep-Dive into On-Premise Low-Privileged LLM Server Deployment** (March 2026).
- **mitmproxy for Fun and Profit** (March 2026) — protocol interception across Linux/Android/iOS.

---

## Strategic synthesis

These seven sources cover roughly **80% of the substantive offensive-research output worth tracking**. If you can only follow three: Trail of Bits + SpecterOps + Synacktiv covers AppSec, AD/red-team, and exploit-dev respectively with minimal duplication.
