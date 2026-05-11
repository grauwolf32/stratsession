# Security newsletters / aggregators

Newsletters are the **time-budget optimization layer** for security reading. Subscribe to two or three and they'll surface most of the other blogs in this directory automatically.

---

## tl;dr sec (Clint Gibler) — https://tldrsec.com/

**Why it matters:** The single most-cited security newsletter. Clint Gibler at Semgrep curates with an AppSec / cloud / offensive lens that exactly matches the scope of this report. Weekly issues. **If you read one newsletter, read this.**

Recent issues (themes):

- **#327 (May 7, 2026)** — Finding zero-days with public AI models; third-party package security.
- **#326 (Apr 30, 2026)** — AI systems automatically creating vulnerability PoCs; GitHub repo code-execution vulnerabilities.
- **#325 (Apr 23, 2026)** — Replicating Mythos bugs using public models; building security programs with minimal budget.
- **#324 (Apr 16, 2026)** — OpenAI's cyber-focused model release; GitHub Actions security hardening.
- **#323 (Apr 9, 2026)** — Anthropic's Mythos model discovering thousands of vulnerabilities; **LLM democratization of vulnerability research** (the single dominant theme of spring 2026).
- **#322 (Apr 2, 2026)** — GitHub's supply-chain security roadmap; AI-assisted vuln-management automation.
- **#321 (Mar 26, 2026)** — AI agent sandboxing approaches; supply-chain compromise incidents.
- **#320 (Mar 19, 2026)** — Security agents fixing bulk vuln issues; detecting malicious open-source contributions.
- **#319 (Mar 12, 2026)** — Future of security in the AI era; Claude model identifying Firefox vulnerabilities.
- **#318 (Mar 5, 2026)** — AI autonomously compromising CI/CD pipelines; security-focused code analysis rules.

**Dominant 2026 theme across all issues:** AI models autonomously finding vulnerabilities at scale. If you only need one signal for the AI-and-AppSec convergence direction, this is it.

**Format:** weekly email + web archive. Each issue is structured (📚 reads / 🛠️ tools / 🤔 commentary). Easy to skim.

**Tl;dr sec also runs `#tldrsec` on Slack** — community of subscribers; tracks live discussion of incidents.

---

## Risky Business (Patrick Gray) — https://risky.biz/ and https://news.risky.biz/

**Why it matters:** Daily-bulletin + weekly-essay format. Patrick Gray + Tom Uren cover security news with a *policy + threat-intel + business* angle, which complements the technical newsletters. Distinct from tl;dr sec — read both.

Recent issues:

- **Risky Bulletin: FCC relaxes foreign router ban to allow for security updates** (May 11, 2026) — regulatory/policy angle.
- **Google patches Android remote takeover bug** (May 8, 2026).
- **Srsly Risky Biz: After Mythos, US Government Weighs AI Model Regulation** (May 7, 2026) — *important policy framing*. The Mythos story (AI vuln-finding) is now triggering regulatory conversations.
- **Extremely targeted supply chain attack hits DAEMON Tools** (May 6, 2026).
- **DigiCert hacked with a malicious screensaver file** (May 4, 2026).
- **The mysterious hack of Moldova's healthcare database** (May 1, 2026).
- **Srsly Risky Biz: US Vows to Fight Distillation Attacks** (Apr 30, 2026) — AI security policy.
- **UK NCSC blasts SOC metrics** (Apr 29, 2026) — *useful for security-program leadership conversations*.
- **New fingerprinting technique can track Tor users** (Apr 27, 2026).
- **There are now SIM-Farm-as-a-Service providers** (Apr 24, 2026) — emerging attack-infrastructure.

**Format:** daily-ish "Risky Bulletin" newsletter + weekly "Srsly Risky Biz" essay + podcast.

---

## Other newsletters worth knowing exist

These didn't get full coverage here but are worth subscribing to depending on focus:

- **Return on Security (RoS)** — Mike Privette's market / vendor / funding focus. Useful for tooling-roadmap context (what's getting funded).
- **CloudSec Reflections** — cloud-security focused (less frequent).
- **Last Week in AWS Security** (companion to Corey Quinn's *Last Week in AWS*) — AWS-specific.
- **Programmingdigest / Console.dev Security issues** — irregular but covers developer-tools-side security.
- **OffSec / Pentest newsletters** — typically less novel than tl;dr sec; skip unless you want pentest-cert-specific content.

---

## Strategic reading-time allocation

For a security-program leader who has **~4 hours/week** for non-incident reading:

| Time | Source | Why |
|---|---|---|
| 30 min | tl;dr sec weekly issue | Best aggregator for AppSec / cloud / offensive |
| 15 min | Risky Business "Srsly Risky Biz" weekly | Policy + threat-actor framing |
| 15 min | Watchtowr feed scan | Enterprise N-day landscape |
| 30 min | Trail of Bits new posts | Tool releases + methodology |
| 30 min | Project Zero new posts (when published) | Mobile/OS 0-click ground truth |
| 30 min | One of: Wiz / Sysdig / Datadog | Cloud-native runtime threat ground truth |
| 30 min | One of: SpecterOps / Synacktiv | AD / red-team / Windows research |
| 30 min | OWASP & CNCF project release notes | What's actually shipping in OSS security tools |
| 30 min | Buffer for incident-response reading | When the week has a major disclosure |

This budget keeps you operationally current without drowning in research-paper depth.
