# Supply chain / SCA / SAST blogs

This was the **single most active category** in 2025–2026. Every major OSS package registry (npm, PyPI, Hugging Face, Docker Hub) saw industrialized supply-chain attacks. Three named campaigns dominate the reading list:

- **TeamPCP** — PyPI → npm → GitHub Actions; LiteLLM / Telnyx / xinference / Bitwarden CLI / Trivy / Checkmarx all compromised.
- **Shai-Hulud / Mini Shai-Hulud** — self-propagating worm across 25,000+ GitHub repos; SAP-targeted variant follow-up.
- **axios npm compromise** (March 2026) — North Korea / Sapphire Sleet attributed; cross-platform RAT distributed via 1.14.1 + 0.30.4.

---

## JFrog Security Research — https://research.jfrog.com/

**Why it matters:** JFrog operates the largest commercial Artifactory registry, which gives them direct visibility into package-registry compromises. Their research is operationally relevant — they detect these in customers' real registries.

Recent notable posts:

- **js-logger-pack Operator Turns Hugging Face into a Malware CDN** (April 2026) — malicious npm package using **private Hugging Face datasets** for exfiltration. Important new pattern: *attackers using HF as TLS-protected, never-scanned C2 surface*.
- **TeamPCP Campaign Spreads to npm via Hijacked Bitwarden CLI** (April 2026) — `@bitwarden/cli v2026.4.0` compromised.
- **TeamPCP Strikes Again: Xinference PyPI Package Compromised** (April 2026) — versions 2.6.0-2.6.2.
- **Astral Injection: XWorm RAT via npm and Discord** (April 2026) — multi-vector campaign.
- **hermes-px: Privacy AI Proxy Steals Prompts** (April 2026) — PyPI package exfiltrating user prompts.
- **Critical Chaos-Mesh vulnerabilities** (September 2025) — K8s cluster takeover via Chaos-Mesh.
- **CVE-2025-29927 Next.js Authorization Bypass** (March 2025) — extensively cross-referenced (Assetnote, Datadog).
- **CVE-2024-6197 Curl/Libcurl Use-after-Free** (December 2024).

---

## Snyk Research — https://snyk.io/blog/category/research/

**Why it matters:** Highest commercial-scanner-side observability into package ecosystems. Snyk Research consistently posts within 24–48h of new supply-chain incidents.

Recent notable posts:

- **PyPI Compromise: Bun-Based Credential Stealer** (April 2026) — `lightning` package harvesting credentials.
- **SAP Package Attack via Bun-Based Stealer** (April 2026) — `@cap-js` / `mbt` compromised via Bun runtime exploit.
- **Elementary-Data PyPI Malicious Release** (April 2026) — trojanized data-eng package stealing cloud creds.
- **Axios npm Package Compromise** (March 2026) — the canonical Snyk write-up of the axios incident.
- **ToxicSkills Agent Supply Chain Study** — *1467 malicious payloads + prompt injection vulns in AI agent skill registries*. **First large-scale survey of malicious AI agent skills**.
- **Snyk & Tessl Partnership on Agent Skills Security** (March 2026) — emerging "agent-skills marketplace" security standards.
- **LiteLLM Poisoned Scanner Backdoor** (March 2026) — *attacker compromised the security scanner itself, then backdoored AI lib*.

---

## Semgrep blog — https://semgrep.dev/blog

**Why it matters:** SAST research from the maker of the most-widely-used pattern-based scanner. Distinctively *practical* (how to write rules, how to operate at scale) rather than disclosure-focused.

Recent notable posts:

- **Dynamically Resolve Dependencies for a Full Picture of Your Inventory** (May 2026) — full-inventory dependency resolution.
- **Inside the AI Memories Security Teams Are Writing** (May 2026) — patterns from AppSec teams using LLM "memory" features.
- **AppSec in Pole Position** (May 2026) — customer-interaction synthesis.
- **Shai-Hulud Themed Malware in PyTorch Lightning** (April 2026).
- **Malicious Intercom PHP Package via Composer Plugin** (April 2026).
- **NIST No Longer Enriching CVEs** (April 2026) — *strategic* piece on NVD decline.
- **SAP Cloud Build Tool Compromised** (April 2026) — Bun-runtime obfuscated payload.
- **How-to Write Skills for Secure AI-Generated Code** (April 2026) — guidance on agent-side security rules.
- **Introducing Semgrep Custom Workflows** — AI + deterministic-analysis combo.
- **Semgrep Autofix Public Beta** — contextual upgrade guidance, line-level breaking-change analysis.

---

## GitHub blog (Security section + GitHub Security Lab) — https://github.blog/security/ and https://github.blog/tag/github-security-lab/

**Why it matters:** Platform-side visibility. GitHub Security Lab's **Taskflow Agent** is the year's most consequential OSS release in AI-assisted vuln triage.

Recent notable posts:

- **Securing the git push pipeline — critical RCE** (April 2026) — validation+patch+investigation in <2 hours.
- **Hack the AI agent: Build agentic AI security skills with the GitHub Secure Code Game** (April 2026) — free OSS game teaching agentic-AI vuln identification.
- **How exposed is your code? Find out in minutes—for free** (April 2026) — **Code Security Risk Assessment** tool — free org-vuln-visibility scan.
- **Securing the open source supply chain across GitHub** (April 2026) — GitHub's upcoming supply-chain protection roadmap.
- **A year of open source vulnerability trends: CVEs, advisories, and malware** (March 2026) — reviewed advisories at 4-year low, but **malware advisories increased significantly**.
- **GitHub expands application security coverage with AI‑powered detections** (March 2026) — CodeQL + AI working together across additional languages/frameworks.
- **Investing in the people shaping open source** (March 2026) — funding update (Alpha-Omega partnership).
- **How to scan for vulnerabilities with GitHub Security Lab's open source AI-powered framework** (March 2026) — **Taskflow Agent**: authentication bypasses, IDORs, token leaks. **First-rank AI-assisted vuln scanner OSS release in this window**.
- **AI-supported vulnerability triage with the GitHub Security Lab Taskflow Agent** (January 2026) — Taskflow for GitHub Actions + JavaScript projects.
- **Community-powered security with AI** (January 2026) — OSS framework release post.
- **Bugs that survive the heat of continuous fuzzing** (December 2025) — analysis of why long-enrolled OSS-Fuzz projects keep retaining vulns.
- **Strengthening supply chain security: Preparing for the next malware campaign** (December 2025) — protective guidance pre-axios.

---

## Binarly — https://www.binarly.io/blog

**Why it matters:** Specialist firmware/UEFI/supply-chain research. PKfail and LogoFAIL were both Binarly disclosures. Their **Transparency Platform** tooling is the canonical firmware-side SBOM analyzer.

Recent notable posts:

- **Scaling YARA Detections with Binarly Transparency Platform v3.5** (October 2025) — YARA integration for malware detection in software supply chains.
- **Cryptographic Algorithms Identification in Java Bytecode** (October 2025) — PQ transition; identify crypto in compiled artifacts.
- **Missing Mitigations: Inside The Security Gap in UEFI Firmware** (October 2025) — software-side mitigations *absent* in firmware.
- **Binarly Transparency Platform: A Next-Generation Approach to Reachability Analysis** (May 2025) — distinguishing exploitable vulns via execution-path analysis.
- **Binarly Transparency Platform v3.0** (April 2025) — vuln prioritization for supply-chain.
- **UEFI Bootkit Hunting** (March 2025) — behavioral analysis + ML clustering for bootkits.
- **Binarly Tracking Updates for CVE-2024-56161** (February 2025) — AMD CPU microcode high-risk flaw.
- **Repeatable Failures: Test Keys Used to Sign Production Software** (September 2024).
- **PKfail: Untrusted Platform Keys Undermine Secure Boot on UEFI Ecosystem** (July 2024) — landmark Secure Boot disclosure.
- **Blind Trust and Broken Fixes: The Ongoing Battle with LogoFAIL Vulnerabilities** (June 2024).

---

## Strategic synthesis for supply-chain

The state-of-2026 reading priority order:

1. **GitHub Security Lab Taskflow Agent** — the year's main OSS release; *evaluate against your existing SAST stack*.
2. **Datadog "dependency cooldowns" post** (linked in `cloud-native.md`) — practical guidance.
3. **JFrog + Snyk + Sysdig coverage of the named campaigns** (TeamPCP, Shai-Hulud, axios). Read one of each per campaign.
4. **Binarly** for firmware / hardware-supply-chain.
5. **Semgrep custom workflows + GitHub AI detections** for the SAST-side roadmap.

Operational recommendation: **at least one of `JFrog + Snyk` and one of `Sysdig + Datadog` should be on the security-team's RSS feed** to ensure compromised-package incidents reach you within 24 hours, not on Patch Tuesday.
