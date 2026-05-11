# KubeCon + CloudNativeCon North America 2025

**Atlanta, GA · November 10–13, 2025**

Largest cloud-native event of the year. Critical addition in 2025: the first **Open Source SecurityCon** as a dedicated full-day, on Monday Nov 10 — "fostering collaboration on cloud-native and open-source software security." Architecture & policy, secure SDLC, supply chain, identity, and open-source policy were the announced pillars.

Primary pages:
- Schedule: https://kccncna2025.sched.com/list/descriptions
- LF events page: https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/

---

## CNCF project updates with strategic weight

### Kyverno — five new policy resource types
Cortney Nickerson (Nirmata) demoed Kyverno's five new policy types: **ValidatingPolicy**, **ImageValidatingPolicy**, **MutatingPolicy**, **GeneratingPolicy**, **DeletingPolicy**. Materially expands what teams can express in a single policy engine — previously some of these required separate tools.

### Kubewarden — unified policy engine
Robert Sirchia (SUSE) presented Kubewarden as a dynamic admission controller now mixing **Rego, CEL, Wasm, and ordinary policies** with both cluster- and namespace-scoped enforcement and policy groups. Notable as a viable alternative to OPA Gatekeeper for teams that want Wasm-portable rules.

### Copacetic — patch images without rebuilding
Jeremy Rickard (Microsoft) demoed Copacetic patching container-image vulnerabilities directly using scanner output. Removes the "wait for upstream rebuild" gap that has been a chronic remediation bottleneck.

### Falco + StratoShark
Gerald Combs (Wireshark Foundation) showed StratoShark, a Wireshark-style forensic capture interface for Falco. Falco rule fires → targeted syscall capture for replay/analysis. Bridges runtime detection and IR in one tool.

### OPA performance
Philip Conrad presented post-1.0 performance gains in Open Policy Agent. Relevant if you're hitting policy-eval latency budgets on hot admission paths.

---

## "Trust beyond containers" — identity & supply chain themes

KubeCon NA 2025's broader narrative (per GitGuardian and Solo.io recaps): **authorization is moving into application logic**, and **operational security is converging with AI governance**. Notable announcements:

- **AuthZed / SpiceDB Enterprise** positioned as authorization backbone for multi-agent / multi-service architectures.
- **Teleport** added visual RBAC mapping + AI-assisted security investigations.
- **Minimus** — contractual zero-CVE distroless image guarantees via continuous rebuild.
- **Cloudsmith** — security-first artifact management & dependency governance.
- **Linkerd** — extended to **Model Context Protocol (MCP)** and Windows, aligning service-mesh with AI agent traffic.
- CNCF announced **$3M+ in project-security investments** through partnerships.

---

## What to do with this

- **If you run Kubernetes in production:** evaluate Kyverno's new policy types against your existing Gatekeeper/Polaris stack — a real chance to consolidate.
- **If your remediation pipeline blocks on rebuilds:** Copacetic is the strongest 2025 candidate for direct image patching.
- **If you have SIEM blind spots in containers:** Falco + StratoShark + Tetragon (eBPF) is now a coherent stack (separately) for detection → forensics → kernel observability.
- **If you're deploying AI agents on the cluster:** Linkerd-for-MCP and SpiceDB are early but on-the-right-track signals; track maturity quarterly.

---

## Sources
- KubeCon NA 2025 schedule: https://kccncna2025.sched.com/list/descriptions
- Solo.io highlights: https://www.solo.io/blog/highlights-from-kubecon-cloudnativecon-north-america-2025
- theCUBE wrap: https://thecuberesearch.com/kubecon-cloudnativecon-north-america-2025-wrap-up/
- GitGuardian "Trust Beyond Containers": https://blog.gitguardian.com/kubecon-2025/
- TechTarget hub: https://www.techtarget.com/searchitoperations/conference/KubeCon-CloudNativeCon-news-coverage
