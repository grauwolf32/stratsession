# Hexacon 2025

**Paris · October 6–12, 2025 (15 talks, single track)**

Heavy-hitting technical offensive-security conference; like OffensiveCon, this is **signal-not-tools**: what the top researchers are exploiting, not OSS to bring home. Most material this year was Pwn2Own follow-ups + hardware/firmware compromise.

Primary pages:
- 2025: https://2025.hexacon.fr/
- Speakers: https://2025.hexacon.fr/conference/speakers/
- Speedrun CTF repo: https://github.com/hexacon-fr/speedrun-2025
- Randorisec recap: https://blog.randorisec.fr/conference-hexacon-2025/

---

## Headline disclosures

### ReVault — Dell ControlVault3 compromise across 100+ models
Philippe Laulheret demonstrated full compromise of the **ControlVault3** secure SoC shipped on 100+ Dell business laptops. Low-privilege user can fully compromise the chip and achieve Windows persistence. Cross-listed with Black Hat USA 2025.

### Cypherock X1 hardware wallet
Sergei Volokitin disclosed an out-of-bounds write in the USB packet-processing logic of the **Cypherock X1** hardware wallet allowing malware to extract private keys in real time. Source for the X1 is on GitHub.

### CUDA de Grâce — AI infrastructure GPU exploit chain
Valentina Palmiotti, Samuel Lovejoy released **NVIDIA CUDA driver 0-days** discovered via fuzzing, enabling container escape on multi-tenant GPU compute. Single most strategically important talk for AI-infrastructure operators in 2025.

### NTLM reflection is dead, long live NTLM reflection
Wilfried Bécard published **CVE-2025-33073** — authenticated RCE affecting Windows and Kerberos via LSASS NTLM auth provider. Survives prior NTLM-reflection mitigations.

### Linux kernel io_uring déjà vu
Pumpkin analyzed **CVE-2025-21836** — race condition in io_uring memory mapping; security patches over multiple generations *created* the new bug via RCU misuse + refcount issues.

### RbTree Family Drama — Linux kernel 0-day
William Liu, Savino Dicanosa demonstrated exploitation of **CVE-2025-38001** (Linux network scheduler), introducing a novel red-black-tree attack technique converting an infinite-loop bug into UAF, defeating modern kernel hardening.

### MediaTek Wi-Fi authentication bypass
Xiaobye disclosed MediaTek Wi-Fi vulnerabilities allowing unauthenticated attackers to skip pairwise master-key validation — auth bypass and RCE without credentials.

### Pwn2Own follow-ups
- **Firefox SpiderMonkey "undefined fields"** — Tao Yan, Edouard Bochin (Pwn2Own Berlin 2025).
- **Redis Lua 2-bit reset → 0-click RCE** — Benny Isaacs (Pwn2Own). 15-year-old UAF in Lua interpreter; 100% reliability bypassing ASLR, PointerGuard, CET.
- **VirtualBox exploit** — HanseoKim (PrisonBreak).
- **Crash One — StarBucks Story (CVE-2025-24277)** — Csaba Fitzl, Gergely Kalman. macOS osanalyticshelper LPE + sandbox escape via XPC + ACL + race conditions.

### Mobile / OS / firmware
- **Apple Secure Enclave Processor in 2025** — Quentin Salingue. Public reference on PAC, Trusted Boot Monitor for current SEP.
- **Paint it Blue: Attacking the Bluetooth stack** — Mehdi Talbi, Etienne Helluy-Lafont. CVE-2023-40129 Android GATT integer overflow → RCE without pairing (Samsung + Xiaomi).
- **Where the shells land** (keynote) — Donncha Ó Cearbhaill (Amnesty International). Forensic perspective on in-the-wild iOS / Chrome / Android / Linux exploitation; Amnesty Security Lab has surfaced 12+ ITW exploits.

### Opening keynote
Ivan Krstić (Apple). No abstract.

---

## What this tells us about the next 12 months

1. **AI infrastructure is exploitable at the driver layer.** CUDA driver 0-days are the year's most strategically important finding for anyone running multi-tenant GPU compute (cloud providers, internal ML platforms).
2. **Secure elements aren't safe.** Two distinct compromises (ControlVault3 + Cypherock X1) show that "hardware root of trust" still leaves a bigger attack surface than typically assumed in TPM/HSM-based threat models.
3. **Mitigations introduce bugs.** io_uring déjà-vu and NTLM reflection sequel illustrate the "patch debt" pattern — each round of mitigation can produce the *next* CVE class.

---

## Sources
- Hexacon 2025 main: https://2025.hexacon.fr/
- Speakers: https://2025.hexacon.fr/conference/speakers/
- Randorisec recap: https://blog.randorisec.fr/conference-hexacon-2025/
- Speedrun CTF repo: https://github.com/hexacon-fr/speedrun-2025
