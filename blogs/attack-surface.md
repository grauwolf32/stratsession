# Attack-surface & enterprise N-day blogs

The "drumbeat of enterprise software RCEs" sources. These shops disclose-and-publish at high frequency, often with full PoCs. They are the canonical reference for what is being actively weaponized against enterprise stacks *right now*.

---

## Watchtowr Labs — https://labs.watchtowr.com/

**Why it matters:** Highest cadence of enterprise N-day disclosures. Distinctive funny-titled write-ups (which makes them quick to recognize in feeds). Each post typically lands when the vendor patch lands or shortly after.

Recent disclosures (titles below are abbreviated):

- **cPanel & WHM Authentication Bypass — CVE-2026-41940** (April 2026).
- **Progress ShareFile Pre-Auth RCE Chain — CVE-2026-2699 & CVE-2026-2701** (April 2026).
- **Citrix NetScaler CVE-2026-3055 Memory Overread Part 1 & 2** (March 2026).
- **GNU inetutils Telnetd CVE-2026-32746 Pre-Auth RCE** (March 2026) — 32-year-old bug in the Telnet daemon.
- **BMC FootPrints Pre-Auth RCE Chains** (March 2026) — ITSM platform exploitation.
- **Juniper Junos Evolved CVE-2026-21902 Pre-Auth RCE** (March 2026).
- **SolarWinds Web Help Desk Pre-Auth RCE** (February 2026).
- **Ivanti EPMM Pre-Auth RCEs CVE-2026-1281 & CVE-2026-1340** (January 2026) — actively exploited.
- **SmarterTools SmarterMail Auth Bypass WT-2026-0001** (January 2026).
- **SolarWinds Supply Chain Attack Analysis ("8 Million Requests Later")** (February 2025).

**Pattern to take away:** If you operate any of cPanel, Citrix NetScaler, BMC, Juniper, Ivanti, SolarWinds, or any pre-auth-RCE-prone perimeter appliance — *subscribe to Watchtowr*. The disclosures are typically published *with* the patch, so they are operational reading, not academic.

---

## Assetnote — https://www.assetnote.io/resources/research

**Why it matters:** Australia-based shop, very strong on enterprise web stack pre-auth RCEs. Many of the high-profile 2024–2025 enterprise vuln chains (Sitecore, ServiceNow, Magento, FortiGate, Citrix) trace to Assetnote write-ups.

Recent notable posts:

- **Doing the Due Diligence: Analyzing the Next.js Middleware Bypass (CVE-2025-29927)** — authn bypass in Next.js middleware. The de-facto reference write-up for that vuln class.
- **Nginx/Apache Path Confusion to Auth Bypass in PAN-OS (CVE-2025-0108)** — web-server path-handling auth bypass.
- **How an obscure PHP footgun led to RCE in Craft CMS**.
- **Advisory: Next.js SSRF (CVE-2024-34351)**.
- **Citrix Denial of Service: Analysis of CVE-2024-8534**.
- **Leveraging An Order of Operations Bug to Achieve RCE in Sitecore 8.x - 10.x**.
- **Chaining Three Bugs to Access All Your ServiceNow Data**.
- **Why nested deserialization is harmful: Magento XXE (CVE-2024-34102)**.
- **Digging for SSRF in NextJS apps**.
- **Two Bytes is Plenty: FortiGate RCE with CVE-2024-21762**.
- **Continuing the Citrix Saga: CVE-2023-5914 & CVE-2023-6184**.

**Read pattern:** Assetnote posts tend to be **methodology + walkthrough** rather than headline-grabbing. They are some of the best teaching material for web-app pentest training.

---

## Horizon3.ai Attack Research — https://www.horizon3.ai/attack-research/

**Why it matters:** Auto-pentest vendor with strong attack-research output. Heavy on detailed CVE write-ups + AD deception research. The "Attack Team" name they use is recognizable in the industry.

Recent notable posts:

- **Autonomous AI Cyber Defense You Can Trust in Production** (May 2026) — methodology for productizing AI security.
- **10 Minutes with Claude: RCE in Apache ActiveMQ — CVE-2026-34197** (April 2026) — *the post itself documents using Claude to find an RCE in 10 minutes*. Single best example post on this workflow.
- **When "Read-Only" Isn't: K8s nodes/proxy GET to RCE** (February 2026) — restricted K8s perms → cluster-wide RCE via WebSocket behavior. Important K8s threat-model update.
- **CVE-2025-40551: Another Solarwinds Web Help Desk Deserialization Issue** (January 2026).
- **Defending with AD Tripwires: GOAD Walkthrough** (January 2026) — practical AD deception.
- **Ticket to Shell: Exploiting PHP Filters and CNEXT in osTicket — CVE-2026-22200** (January 2026).
- **CVE-2025-64155: Three Years of Remotely Rooting the Fortinet FortiSIEM** (January 2026).
- **The Ni8mare Test: n8n RCE Under the Microscope — CVE-2026-21858** (January 2026) — *real-world exposure vs. theoretical exposure framing* is a useful template for triage.

---

## Orange Tsai's blog — https://blog.orange.tw/

**Why it matters:** Independent web-security researcher. Lower volume, but each post lands a **landmark attack class**. The work is often cited in PortSwigger's Top 10 Web Hacking Techniques.

Recent posts:

- **The Art of PHP — My CTF Journey and Untold Stories!** (August 2025).
- **從 Web 狗的視角看 OSEE** (July 2025) — web-researcher perspective on the OSEE advanced Windows exploitation cert.
- **WorstFit: Unveiling Hidden Transformers in Windows ANSI!** (January 2025) — major write-up on Windows ANSI character-encoding transformation attacks.
- **Confusion Attacks: Exploiting Hidden Semantic Ambiguity in Apache HTTP Server!** (August 2024) — landmark Apache HTTP server attack class.
- **CVE-2024-4577 — PHP-CGI Argument Injection Great Again** (June 2024) — *the* widely-exploited PHP-CGI vuln; one of the most-weaponized 2024 disclosures.

**Cadence:** ~1 post / 1–3 months but each is high-impact. Worth a manual check every couple of months rather than feed subscription.

---

## How to use this category

These four sources are the **operational feed** — what to patch, what to detect, what to assume is being scanned-for now. Set them up as the highest-priority RSS / mailing-list subscriptions:

1. **Watchtowr** for the enterprise-appliance daily firefight.
2. **Assetnote** for web-stack chain analysis and methodology.
3. **Horizon3** for K8s + identity + AD + integration-attack research.
4. **Orange Tsai** for the once-a-quarter web-security landmark write-up.

This category complements (but does not replace) the offensive-vendor blogs — these are more "what's burning right now" while the vendor blogs are "what tooling and technique to invest in."
