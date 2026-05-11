# Black Hat USA 2025

**Mandalay Bay, Las Vegas · August 2–7, 2025 (Briefings Aug 6–7; Arsenal Aug 6–7)**

Reference pages on `blackhat.com/us-25/` return HTTP 403 to web-fetch tooling — this writeup is assembled from press coverage, OpenSSF/CSO/TechTarget recaps, and the awesome-blackhat-arsenal index. Treat tool counts and presenter attributions as **press-sourced**, and verify on the official schedule if making procurement decisions.

- 115+ Arsenal tool demos across Aug 6–7
- 100+ Briefings; main themes: AI agent abuse, browser-native security, enterprise credential-vault flaws, OAuth architecture, 5G baseband, hardware secure-element compromise, space systems

Primary pages:
- Briefings schedule: https://blackhat.com/us-25/briefings/schedule/ (403 from WebFetch — accessible in browsers)
- Arsenal schedule: https://blackhat.com/us-25/arsenal/schedule/
- Closing announcement: https://blackhat.com/html/press/2025-08-13.html

---

## High-impact Briefings & disclosures (verifiable from coverage)

### Enterprise credential vaults — Cyata research
Cyata disclosed a chain of logic flaws in **HashiCorp Vault** and **CyberArk Conjur** authentication, validation, and policy-enforcement. Single most-cited "real product, real prod impact" disclosure of the show.

### Dell ControlVault3 / "ReVault" — Talos / Philippe Laulheret
Firmware flaws across **100+ Dell business laptop models** in the hardware secure-element designed to protect biometrics, passwords, and other secrets. Same researcher also presented at Hexacon 2025 with the full chain.

### AgentFlayer — Zenity
Zenity demonstrated vuln chains exploiting rogue prompts in flagship enterprise AI assistants (**ChatGPT, Gemini, Microsoft Copilot**), including **0-click** variants. The most-discussed "agent attack" research of 2025.

### "From Prompts to Pwns: Exploiting and Securing AI Agents"
End-to-end LLM/agent attack lifecycle — became the de-facto reference talk for agent threat modeling.

### Other notable briefings
- **Wormable AirPlay vulnerability** (Oligo).
- **5G baseband flaws** enabling unauthenticated RCE across multiple chipsets.
- **OAuth architecture hardening** sessions (auth-platform-side, not just relying-party).
- **Smart-tractor hacking** (John Deere ecosystem) — supply-chain + right-to-repair crossover.
- **VisionSpace — space mission-ending vuln chain.**
- **SquareX browser security** disclosures (cross-listed with DEF CON 33).

---

## Arsenal — open-source tooling

The official Black Hat Arsenal repo (`toolswatch/blackhat-arsenal-tools`) tracks the corpus historically; the per-event 2025 listings live in `tools/USA/2025/` in `elbraino/awesome-blackhat-arsenal`. From press coverage and OpenSSF's BH USA 2025 recap, confirmed Arsenal-floor items include:

- **SigmaOptimizer** — Sigma rule optimization / generation tooling.
- **Hayabusa** — Windows event log fast-forensics scanner (Yamato Security project family).
- **Suzaku** — cloud audit-log fast-forensics scanner (companion to Hayabusa).
- **Buttercup** (Trail of Bits AIxCC CRS) — also demoed/discussed in BH USA + DEF CON ecosystem.
- **OpenSSF AIxCC booth** showcased the seven AIxCC CRSs.
- Multiple LLM red-team tools demoed: **Promptfoo**, **GARAK**, **PyRIT**, **DeepTeam**.

> Many DEF CON 33 Demo Lab tools (Empire 6, C4, FLARE-VM, SAMLSmith, OAuthSeeker, Spotter, KIEMPossible…) presenters were the same week at BH Arsenal — assume major DC33 releases had matching Arsenal slots unless verified otherwise. See `defcon-33.md` for the full catalog.

---

## Why Black Hat USA 2025 mattered strategically

1. **Agent attacks went mainstream.** Zenity AgentFlayer + multiple agent-platform talks shifted enterprise AI deployments from "prompt-injection is a niche concern" to "your enterprise copilots are a privileged attacker access path."
2. **Credential-vault posture became a board issue.** Vault + Conjur disclosures arrived in the same week as multiple high-profile secrets-theft incidents; vault rotation hygiene now in question.
3. **Hardware secure elements are not a remediation backstop.** Dell ControlVault3 chain showed the weakest secure-element link compromises everything above it (Windows persistence with low-priv user).
4. **The Las Vegas week is now an OSS release event.** Companies time releases of Empire/Metasploit/FLARE-VM/Falco/CycloneDX updates to land in this window — track BH USA + DEF CON as a single release surface for inventory.

---

## Sources
- Black Hat USA 2025 press recap: https://blackhat.com/html/press/2025-08-13.html
- CSO Online "5 key takeaways": https://www.csoonline.com/article/4037869/5-key-takeaways-from-black-hat-usa-2025.html
- TechTarget BH USA 2025 hub: https://www.techtarget.com/searchsecurity/conference/Guide-to-the-latest-Black-Hat-Conference-news
- Red Canary BH USA 2025 preview: https://redcanary.com/blog/security-operations/black-hat-2025/
- OpenSSF BH USA + DC33 recap (AIxCC focus): https://openssf.org/blog/2025/08/14/openssf-at-black-hat-usa-2025-def-con-33-aixcc-highlights-big-wins-and-the-future-of-securing-open-source/
- NTT DATA Arsenal speaker note: https://www.nttdata.com/global/en/insights/event/2025/august/nttdata-cert-member-presents-arsenal-session-at-black-hat-usa-2025
- ToolsWatch Arsenal repo: https://github.com/toolswatch/blackhat-arsenal-tools
- Awesome BH Arsenal index: https://github.com/elbraino/awesome-blackhat-arsenal
