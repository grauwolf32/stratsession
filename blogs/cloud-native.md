# Cloud-native security blogs

The vendor research teams in this space have **very different angles**:

- **Wiz** — vuln research that lands in their CSPM product (Security Graph), high-cadence kernel + cloud CVE work.
- **Aqua Nautilus** — Linux/container runtime threat research.
- **Sysdig TRT** — cloud-native threats + cryptojacking + LLMjacking research.
- **Datadog Security Labs** — detection-engineering-heavy + cloud + supply-chain.
- **Google Cloud Identity & Security blog** — vendor product / strategy side.

Read all five for a complete cloud-native threat picture.

---

## Wiz Research — https://www.wiz.io/blog

**Why it matters:** Currently the highest-cadence cloud-vuln-research output of any vendor. Notable for landing kernel LPEs and PAN-OS/critical-appliance CVEs back-to-back.

Recent notable posts:

- **AI Threat Readiness Framework** (May 2026) — claim: "AI models now find and exploit zero-days autonomously"; framework for accelerated patching.
- **Dirty Frag: Linux Kernel Privilege Escalation** (May 2026) — unpatched kernel vuln chain enabling root escalation across major distros.
- **Wiz-Akamai Integration** (May 2026) — edge configuration in the Security Graph; *interesting precedent for edge↔runtime visibility*.
- **Jenkins Threat Landscape** (May 2026) — Jenkins attack surface analysis through usage patterns + plugin adoption.
- **PAN-OS Critical Buffer Overflow CVE-2026-0300** (May 2026) — unauth RCE with root in Palo Alto.
- **Copy Fail Linux LPE — CVE-2026-31431** (May 2026) — kernel LPE; *also covered by Microsoft Security and Sysdig in the same week — triple confirmation of significance*.
- **Mini Shai Hulud Supply Chain Attack** (April 2026) — malicious npm packages targeting SAP.
- **State of AI in Cloud 2026** (April 2026) — report.
- **GitHub RCE Vulnerability — CVE-2026-3854** (April 2026) — critical flaw in GitHub git infrastructure.
- **NIST NVD Update** (April 2026) — shift from static CVE scoring → risk-based prioritization.

---

## Aqua Nautilus — https://www.aquasec.com/blog/

**Why it matters:** Runtime threat research; Trivy maintainer side. Strong on Linux container malware + emerging attack patterns.

Recent notable posts (titles inferred from index):

- **Autonomous Runtime Security: Turning Runtime Intelligence into Agentic Response** — autonomous response framing piece.
- **Unveiling the Mythos Behind Runtime Security** — Mythos model adversarial-time framing.
- **Trivy investigation update** — incident-response for Trivy itself; verify against `aquasec/trivy` advisories.
- **When AI Writes, Scans and Fixes Code, Runtime Becomes the Last Line of Defense** — "Claude found over 500 high-severity vulnerabilities in production open-source codebases."
- **Critical CVE in React Server Components Actively Exploited — CVE-2025-55182** — React 19 / Next.js RCE.
- **How to Set Up Runtime Protection Against Malware Like Kaiji** — Linux server malware defense.
- **Selective Memory Dump Technique for Deeper Container Forensic Analysis**.
- **Aqua at KubeCon 2025: Securing Cloud Native and AI Apps**.
- **Security That Speaks Your Language: Trivy MCP Server** — Trivy as an MCP server callable from AI agents. *Notable: this is the first major OSS scanner shipped with native MCP support*.

---

## Sysdig TRT — https://www.sysdig.com/threat-research

**Why it matters:** The Threat Research Team has published some of the most-cited cloud-threat operations of the past few years (PURPLEURCHIN cryptojacking, LLMjacking, AMBERSQUID, Scarleteel). Cadence is lower than Wiz but each post is meaty.

Recent notable posts:

- **Dirty Frag — CVE-2026-43284 and CVE-2026-43500** (May 2026) — co-reported with Wiz; unpatched Linux kernel LPE via ESP and RxRPC.
- **CVE-2026-31431 "Copy Fail"** (April 2026) — same kernel LPE seen at Wiz; Sysdig TRT contributed detection content.
- **CVE-2026-42208: SQL Injection in LiteLLM** — LLM stack supply chain attack.
- **CVE-2026-39987: Marimo Weaponization** — blockchain botnet deployed via weaponized marimo notebooks on HuggingFace.
- **Marimo RCE Exploitation** — pre-auth RCE in marimo; *full interactive shell on exposed instances in <10 hours from disclosure*.
- **TeamPCP Supply Chain Expansion** — compromise spreading from Trivy to Checkmarx GitHub Actions repos. **Major 2026 supply-chain incident; cross-reference with JFrog + Snyk posts in `supply-chain.md`**.
- **AI Coding Agents Security** — detection gaps for AI agents executing on developer machines without behavioral baselines.
- **CVE-2026-33017: Langflow RCE** (March 2026) — Langflow AI framework unauthenticated RCE → arbitrary Python.
- **Ingress-Nginx Configuration Injection — CVE-2026-3288 / CVE-2026-24512** (March 2026).
- **LLMjacking Marketplace Evolution** — industrialization of LLM credential theft.
- **AI-Assisted Cloud Intrusion** (November 2025) — threat actors achieving AWS admin in <10 minutes leveraging LLMs.
- **Shai-Hulud Worm Return** (November 2025) — self-propagating malware across 25,000+ GitHub repos.
- **React2Shell RCE Detection — CVE-2025-55182** (December 2025).
- **EtherRAT** — Ethereum-based implant in React2Shell attacks; blockchain-blended C2 (DPRK attribution).

**Read pattern:** Sysdig TRT posts pair well with the corresponding JFrog / Snyk / Datadog write-ups for the same incident — typically each adds a different angle (detection rule, supply-chain analysis, runtime observation).

---

## Datadog Security Labs — https://securitylabs.datadoghq.com/articles/

**Why it matters:** Detection-engineering-heavy posts. Their content emphasizes the *defender* path more than the offensive vendors do — useful complement.

Recent notable posts:

- **Kubernetes security fundamentals: Secrets** (May 2026).
- **The case for dependency cooldowns in a post-axios world** (April 2026) — *practical recommendation post* on the supply-chain-pinning topic. **Worth reading even if you read nothing else from Datadog**.
- **Unpatchable Vulnerabilities of Kubernetes: CVE-2020-8562** + **CVE-2020-8561** (April + March 2026) — two-post series on architectural K8s vulns that *cannot be patched*. Crucial threat-modeling input.
- **Compromised axios npm package delivers cross-platform RAT** (March 2026) — incident write-up of the year's biggest npm supply-chain attack.
- **LiteLLM and Telnyx compromised on PyPI** (March 2026) — TeamPCP campaign.
- **Uncovering agent logging gaps in Copilot Studio** (March 2026) — responsible-disclosure write-up of Azure AI logging.
- **Behind the console: Active phishing campaign targeting AWS** (March 2026).
- **Hook, line, and vault: A technical deep dive into 1Phish** (February 2026).
- **Kubernetes project issues warning on Ingress NGINX retirement** (February 2026).

---

## Google Cloud Security blog — https://cloud.google.com/blog/products/identity-security

**Why it matters:** Vendor-strategy side; less useful for technical detail, but the canonical reference for what Google is shipping in Cloud + Security AI.

Recent notable themes (less per-post detail because most posts are product announcements):

- **Wiz + Google Cloud integration** (Next '26 announcement) — Wiz is now Google-owned; this is the strategic merger reshaping CSPM in 2026.
- **Google Cloud Fraud Defense, next evolution of reCAPTCHA**.
- **What's new in IAM** — governance + runtime defense updates.
- **Agent Gateway ISV ecosystem** — for security + governance.
- **Guardrails at the gateway: Securing AI inference on GKE with Model Armor**.
- **Raising the security baseline: AI + cloud security on by default**.

---

## Strategic synthesis for this category

1. **Wiz + Sysdig** are the most-likely-to-co-disclose duo on kernel/cloud CVEs. Read both for the same incident.
2. **Datadog** is the best blog for **operationalizing detection** out of disclosed incidents.
3. **Aqua** is the best blog for **runtime malware research** specifically (Kaiji, container forensics).
4. **PAN-OS, GitHub, Linux kernel** are the three platforms with the most-recent critical-severity cloud-impacting CVEs in this window — establish patch-cadence procedures for them.
5. **TeamPCP + Shai-Hulud + axios** are the three named supply-chain campaigns to know — cross-reference in `supply-chain.md`.
