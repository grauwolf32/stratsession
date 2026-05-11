# Web-research blogs

The single most important source in this category is PortSwigger — it deserves its own file because it doubles as the **annual curation engine** for web hacking research.

---

## PortSwigger Research — https://portswigger.net/research

**Why it matters:** James Kettle's research team publishes ~3-6 posts a year, each typically introducing a *new attack class*. The annual **Top 10 Web Hacking Techniques** is the authoritative survey of the year's web security research (community-nominated, expert-judged).

Recent notable posts:

- **The Fragile Lock: Novel Bypasses For SAML Authentication** (December 2025) — new SAML auth bypass technique class. Most consequential SAML research of the year.
- **Introducing HTTP Anomaly Rank** (November 2025) — methodology for ranking irregular HTTP patterns; relevant to both red-team request smuggling and detection engineering.
- **Top 10 Web Hacking Techniques of 2025** (February 2026) — the year's canonical survey. *Reading just this one post each year is the highest-ROI web-research input available*.
- **Top 10 Web Hacking Techniques of 2025 — Nominations Open** (January 2026) — community call.
- **Introducing the URL Validation Bypass Cheat Sheet** (September 2024) — still-current reference.
- **Splitting the Email Atom: Exploiting Parsers to Bypass Access Controls** (August 2024) — landmark email-parser-differential attack technique.

**Recurring themes in PortSwigger output this window:**
- Parser differentials (Email Atom, SAML)
- Protocol-implementation gaps (HTTP Anomaly Rank)
- Request smuggling continued evolution (recurring annually)
- Web cache deception variants

---

## Why no other web-research source has its own file

The web-research category is heavily PortSwigger-centric — most other web-research output is either:

- Bundled into broader vendor blogs (Synacktiv, Assetnote, Watchtowr — see other files);
- Independent posts by researchers like Orange Tsai (see `attack-surface.md`);
- Conference write-ups (see `conferences/`).

PortSwigger's annual *Top 10 Web Hacking Techniques* effectively *aggregates* the entire web-research community for you. Reading PortSwigger + Orange Tsai + the Top 10 list each February is the high-recall, low-noise web-research diet.

---

## Adjacent web-research sources worth knowing exist

These didn't get their own blog write-ups because they post irregularly or are more newsletters:

- **HackTricks** (https://book.hacktricks.xyz/) — wiki/cheatsheet of web-attack techniques, *not* a blog but the closest thing to a comprehensive reference.
- **Sam Curry's blog** (https://samcurry.net/) — high-profile car-hacking and account-takeover research; ~yearly publish cadence.
- **Brett Buerhaus / bbuerhaus** — bug-bounty case studies.
- **PortSwigger's own Daily Swig was discontinued in 2023**; PortSwigger Research is now the canonical home for that content lineage.
