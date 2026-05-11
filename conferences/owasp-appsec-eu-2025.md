# OWASP Global AppSec EU 2025

**Centre de Convencions Internacional de Barcelona (CCIB) · May 26–30, 2025**

700+ attendees. Headline news for the year: a dedicated **Open WAF Day** with CRS + ModSecurity + Coraza in one track.

Primary pages:
- Schedule: https://owasp2025globalappseceu.sched.com/list/simple
- OWASP events: https://owasp.org/events/

---

## Open WAF Day & rule-language overhaul (May 28)

Single-track day on the open WAF stack:

- **OWASP ModSecurity in Motion: Evolving the Open Source WAF** (Ervin Hegedus) — Thursday May 29, 11:00 AM, Room 133-134.
- **Beyond the Rules: The Past, Present, and Future of OWASP CRS** (Felipe Zipitria) — Fri May 30, 10:30 AM, Room 133-134.
- **OWASP Coraza in 2025: What next for the WAF you want to use?** (Soujanya Namburi) — Thu 2:45 PM, Room 133-134.

The Coraza roadmap signals the WAF community's pivot away from C-based ModSecurity for new deployments; CRS rule-language rework is the long-term migration path.

## OWASP CycloneDX — major announcements

- **OWASP CycloneDX Hackathon with Transparency Exchange API** (Olle E. Johansson) — Wed May 28, 9:00 AM, Room 127. Hands-on with the cross-tool exchange protocol that pairs with CycloneDX.
- **Sunshine — new SBOM visualization tool by OWASP CycloneDX** (Luca Capacci, Mattia Fierro) — Thursday 1:15 PM, Room 133-134. The first official OSS visualizer for the format — closes a major usability gap. **Worth a POC for any team already producing CycloneDX SBOMs**.

## Other OWASP project releases

- **OWASP Domain Protect Project** (Paul Schwarzenberger, recap) — vulnerable-domain detection + preventative resource creation (e.g., auto-creating dangling-S3 buckets to deny squatters).
- **smithy** — Go tool for automating security-team frameworks.
- **OWASP Juice Shop, DefectDojo, ASVS, Nettacker** — Demo Lab demos across multiple days.
- **OWASP SAMM User Day** with SAMM roadmap talks.

---

## What to take to your team

1. **If you have SBOMs but no one looks at them**: deploy Sunshine. The "we generate them and put them in a bucket" anti-pattern is solvable now.
2. **If you're picking a WAF strategy for the next 3 years**: read the Coraza roadmap and the CRS next-gen rule talks before deciding ModSecurity-vs-Coraza-vs-vendor.
3. **If you care about exposed-domain attack surface**: OWASP Domain Protect is mature enough to integrate into a domain-management pipeline.

---

## Sources
- Schedule: https://owasp2025globalappseceu.sched.com/list/simple
- GenAI Security Project event page: https://genai.owasp.org/event/owasp-global-appsec-eu-2025/
- Personal recap (Adan): https://medium.com/@adan.alvarez/owasp-global-appsec-barcelona-2025-personal-recap-89bed7dc4342
