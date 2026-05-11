# Big-tech / vendor research blogs

These are platform-side research teams. Lower-frequency than independent shops, but every post is *load-bearing* — these are the teams responsible for disclosing platform-level vulns and shaping industry response.

---

## Project Zero — https://projectzero.google/

**Why it matters:** Google's elite vuln-research team. **Lowest cadence, highest impact**. Each post typically documents a complete browser/OS/mobile attack chain with full PoC and write-up.

Recent notable posts:

- **On the Effectiveness of Mutational Grammar Fuzzing** (March 2026) — flaws in coverage-guided grammar fuzzing + mitigations. Methodology paper.
- **A Deep Dive into the GetProcessHandleFromHwnd API** (February 2026) — Windows API used in UAC bypass exploits.
- **Bypassing Administrator Protection by Abusing UI Access** (February 2026) — five privesc bypasses against Windows 11's new admin-protection feature.
- **Breaking the Sound Barrier, Part II: Exploiting CVE-2024-54529** (January 2026) — macOS audio daemon type confusion.
- **Bypassing Windows Administrator Protection** (January 2026) — one of nine admin-privesc vulns found in dedicated research push.
- **A 0-click exploit chain for the Pixel 9 Parts 1-3** (January 2026) — three-part series. Audio decoder RCE → kernel sandbox escape via hw-accel driver → ecosystem-wide 0-click enablers. **Canonical reference for 2026-era mobile 0-click attack surface**.
- **A look at an Android ITW DNG exploit** (December 2025) — in-the-wild Samsung image-parsing vuln.
- **Defeating KASLR by Doing Nothing at All** (November 2025) — kernel-linear-mapping KASLR bypass.

---

## Microsoft Security blog / MSRC — https://www.microsoft.com/en-us/security/blog/ and https://msrc.microsoft.com/blog/

**Why it matters:** Vendor disclosures + threat intel from one of the highest-visibility positions in the industry. Microsoft Defender and Threat Intel teams co-publish here.

Note: msrc.microsoft.com timed out during this research — content sourced from search + Microsoft Security main blog.

Recent notable posts:

- **When prompts become shells: RCE vulnerabilities in AI agent frameworks** (May 2026) — disclosed **CVE-2026-25592 + CVE-2026-26030** in Semantic Kernel; *prompt injection → host RCE; a single prompt can launch calc.exe on a device running an AI agent*. **One of the most important AI-security disclosures of the year**.
- **CVE-2026-31431 "Copy Fail" Linux LPE across cloud environments** (May 2026) — also covered by Wiz and Sysdig the same week.
- **Breaking the code: Multi-stage 'code of conduct' phishing → AiTM token compromise** (May 2026).
- **Email threat landscape: Q1 2026 trends** (April 2026) — *8.3B email phishing threats detected*; **QR-code phishing doubled** over Q1.
- **AI-powered defense for an AI-accelerated threat landscape** (April 2026).
- **Storm-1175 focuses gaze on vulnerable web-facing assets in high-tempo Medusa ransomware operations** (April 2026) — n-day weaponization within 24h of disclosure.
- **Mitigating the Axios npm supply chain compromise** (April 2026) — attribution to Sapphire Sleet (DPRK).
- **Zero Day Quest 2026** (April 2026) — Microsoft's live-hacking event paid out $2.3M; 80+ Cloud/AI security vulns surfaced and remediated.

---

## Mandiant / Google Threat Intelligence — https://cloud.google.com/blog/topics/threat-intelligence

**Why it matters:** Mandiant + Google TAG + VirusTotal under one banner. The deepest IR-grounded research in the industry.

Recent notable posts:

- **Defending Your Enterprise When AI Models Can Find Vulnerabilities Faster Than Ever** — strategic guide on preparing for AI-driven mass-vuln-discovery campaigns.
- **Snow Flurries: How UNC6692 Employed Social Engineering to Deploy a Custom Malware Suite**.
- **The German Cyber Criminal Überfall: Shifts in Europe's Data Leak Landscape**.
- **vSphere and BRICKSTORM Malware: A Defender's Guide** (62-min read) — major IR guide.
- **North Korea-Nexus Threat Actor Compromises Widely Used Axios NPM Package in Supply Chain Attack** — Mandiant's axios attribution write-up.
- **M-Trends 2026: Data, Insights, and Strategies From the Frontlines** — annual IR report.
- **The Proliferation of DarkSword: iOS Exploit Chain Adopted by Multiple Threat Actors** (34-min read).
- **Ransomware Under Pressure: Tactics, Techniques, and Procedures in a Shifting Threat Landscape** (53-min read).
- **Proactive Preparation and Hardening Against Destructive Attacks: 2026 Edition** (222-min read) — comprehensive hardening guide.
- **Look What You Made Us Patch: 2025 Zero-Days in Review** — annual 0-day retrospective.
- **Coruna: The Mysterious Journey of a Powerful iOS Exploit Kit**.

---

## Zero Day Initiative (ZDI) — https://www.zerodayinitiative.com/blog

**Why it matters:** ZDI runs Pwn2Own + buys vulns. Their blog is the canonical reference for Pwn2Own results and monthly Patch Tuesday summaries.

Recent notable posts:

- **CVE-2026-33824: RCE in Windows IKEv2** (April 2026) — TrendAI Research analysis.
- **The April 2026 Security Update Review** — monthly Patch Tuesday roundup. *The most reliable single source for "what landed in this month's MS + Adobe patches"*.
- **Node.js Trust Falls: Dangerous Module Resolution on Windows** (April 2026).
- **Announcing Pwn2Own Berlin for 2026** (March 2026) — AI, NVIDIA, Microsoft, AWS, Linux/macOS targets.
- **The March / February 2026 Security Update Reviews** — monthly.
- **CVE-2026-20841: Arbitrary Code Execution in Windows Notepad** (February 2026).
- **CVE-2025-6978: Arbitrary Code Execution in Arista NG Firewall** (February 2026).
- **Pwn2Own Automotive 2026 — Day 1/2/3 Results** (January 2026).

---

## Strategic synthesis for vendor-research

If you're running a security program:

1. **Project Zero** is irregular — set up notifications, read each post.
2. **Microsoft Security blog** is operationally critical because Windows + Azure + Defender + M365 all funnel through this team. Critical posts (like Semantic Kernel RCE) need same-day attention.
3. **Mandiant / GTIG** is best for **strategic threat-actor briefing material**; the long-form annual reports (M-Trends, Proactive Hardening) are read once a year and reference all year.
4. **ZDI** for **operational patch-Tuesday awareness** — the monthly review post is one of the highest-ROI subscriptions in security.

These four sources between them ≈ cover all major-vendor-side disclosures with high recall. **Subscribe to all four**; the volume is manageable (~3-6 posts/week aggregate).
