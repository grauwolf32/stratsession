# OffensiveCon 2025 & 2026

**Berlin · OffensiveCon 2025: May 16, 2025 · OffensiveCon 2026: May 15–16, 2026**

Single-track, deeply technical conference focused on **vulnerability discovery, advanced exploitation, and reverse engineering**. Tools are rarely released; the value here is **attack-surface signal** and *what classes of bugs the top researchers are spending time on*. Talks usually go to YouTube within a few months.

Primary pages:
- 2025 speakers: https://www.offensivecon.org/speakers/2025/
- 2026 agenda: https://www.offensivecon.org/agenda/2026/
- YouTube: https://www.youtube.com/c/offensivecon

---

## OffensiveCon 2025 (May 16, 2025) — selected talks

### Keynotes
- **Automating Your Job? The Future of AI and Exploit Development** — Perri Adams (DARPA). Set the framing for the AIxCC year — AI's actual capabilities in RE, vuln discovery, and exploit dev.
- **How Offensive Security Made Me Better at Defense** — Dino Dai Zovi. Security-functionality tradeoffs.

### CPU / hypervisor / browser
- **EntrySign: create your own x86 microcode for fun and profit** — Matteo Rizzo, Kristoffer Janke, Josh Eads, Eduardo Vela Nava (Google). x86 CPU microcode exploitation past ring 0 and SMM.
- **Journey to freedom: Escaping from VirtualBox** — Corentin Bayet, Bruno Pujos. VBox hypervisor exploit chained with Windows kernel LPE.
- **Garbage Collection in V8** — Richard Abou Chaaya, John Stephenson. V8 GC as attack surface.
- **Attacking Browsers via WebGPU** — Lukas Bernhard. GPU shader compilation as a huge browser-accessible attack surface.
- **Finding and Exploiting 20-year-old bugs in Web Browsers** — Ivan Fratric. XSLT vulnerabilities across all major browsers.

### Kernel / mobile / firmware
- **Frame by Frame, Kernel Streaming Keeps Giving Vulnerabilities** — Angelboy. Windows Kernel Streaming attack surface.
- **Hunting for overlooked cookies in Windows 11 KTM** — Cedric Halbronn, Jael Koh. Kernel Transaction Manager.
- **Skin in the game: Survival of GPU IOMMU irregular damage** — fish, Ling Hanqin. Adreno/Mali/PowerVR.
- **Chainspotting 2** — Ken Gannon. Samsung Galaxy S24 Pwn2Own Ireland 2024 chain.
- **KernelGP: Racing against the Android kernel** — Chariton Karamitas. Four novel userland techniques to block the Android kernel.
- **Android In-The-Wild: Unexpectedly Excavating a Kernel Exploit** — Seth Jenkins (Google P0). Reverse-engineering ITW exploit from kernel crash logs.
- **Fighting cavities: Securing Android Bluetooth by Red teaming** — Jeong Wook Oh, Rishika Hooda, Xuan Xing. Remote AOSP Bluetooth.
- **No Signal, No Security: Dynamic Baseband Vulnerability Research** — Daniel Klischies, David Hirsch. Released **BaseBridge** extension to the FirmWire baseband emulator for MediaTek RCE work.
- **Breaking the Sound Barrier: Exploiting CoreAudio via Mach Message Fuzzing** — Dillon Franke (Google). macOS sandbox escapes via Mach msg fuzzing.

### Misc
- **Parser Differentials: When Interpretation Becomes a Vulnerability** — joernchen. Parser-implementation differential attack class.

**Public OSS releases:** essentially limited to **BaseBridge** (FirmWire baseband emulator extension). Everything else is research write-ups + PoC drops at speaker's discretion.

---

## OffensiveCon 2026 (May 15–16, 2026)

- 4 preceding training days (May 11–14).
- Co-located with **Pwn2Own Berlin 2026** — >$1M cash + prizes. New AI categories: **AI Databases**, **Coding Agents**, **Local Inferences**, **NVIDIA-specific category**. Expect a flood of new attack-surface signal in the AI-infrastructure space from this competition.

Strategic signal for the next 12 months: **AI-infrastructure exploitation is now a first-class Pwn2Own track**. Track Pwn2Own Berlin 2026 results (mid-May 2026) for the canonical list of exploitable categories.

---

## Sources
- OffensiveCon 2025 speakers: https://www.offensivecon.org/speakers/2025/
- OffensiveCon 2026 agenda: https://www.offensivecon.org/agenda/2026/
- 2025 YouTube playlist: https://www.youtube.com/playlist?list=PLYvhPWR_XYJk0p40BrX7K2z-_j_tJmvhc
- Pwn2Own Berlin 2026: https://www.thezdi.com/blog/2026/3/11/announcing-pwn2own-berlin-for-2026
