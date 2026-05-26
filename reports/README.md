# Per-class deep-dive reports

In-depth exploration of the submodules under [`../sources/`](../sources/), focused on **what each tool actually does that's new or unusual** — not feature-list marketing. Where multiple tools share a class, they are compared side-by-side.

| Report | Class | Tools compared |
|---|---|---|
| [fuzzing.md](./fuzzing.md) | Fuzzing engines & frameworks | AFL++, LibAFL, Ruzzy |
| [ai-vuln-research.md](./ai-vuln-research.md) | AI-driven vulnerability discovery | Buttercup, Seclab Taskflow Agent |
| [waf.md](./waf.md) | Web Application Firewalls | Coraza (engine), Core Rule Set (ruleset) |
| [scanners.md](./scanners.md) | Vulnerability scanners & patch analyzers | Trivy, Trivy MCP, Nettacker, PatchLeaks |
| [api-security.md](./api-security.md) | API discovery + authorization testing | Vespasian, Hadrian |
| [vulnmgmt-sbom.md](./vulnmgmt-sbom.md) | Vulnerability management & SBOM | DefectDojo, Sunshine |
| [reference-design.md](./reference-design.md) | Reference designs & training labs | SafeUpdater (Electron), DVBE (Damn Vulnerable Browser Extension) |
| [ci-cd-security.md](./ci-cd-security.md) | CI/CD pipeline security (offensive + defensive + credential validation) | SmokedMeat, Plumber, Brutus |
| [cloud-posture.md](./cloud-posture.md) | AWS posture + attack-chain correlation | cloud-audit (vs Prowler) |
| [kubernetes-security.md](./kubernetes-security.md) | Kubernetes / container security (detection + posture + admission) | Falco + StratoShark, Tetragon, Tracee, Spotter, Kyverno, Kubewarden, Copacetic, KIEMPossible |
| [ebpf-runtime-detection.md](./ebpf-runtime-detection.md) | eBPF runtime detection deep-dive (Falco vs Tetragon vs Tracee) | Kernel hooks, policy authoring, enforcement models, production deployment, StratoShark forensics |
| [identity-attack-path.md](./identity-attack-path.md) | Identity / AD / Entra ID attack-path tooling | BloodHound CE, AzureHound, MSSQLHound, EntraGoat, SAMLSmith, OAuthSeeker, maSSO, ForceHound |
| [llm-redteam.md](./llm-redteam.md) | LLM red-team & agent-abuse landscape | Promptfoo, GARAK, PyRIT, DeepTeam, promptmap2, MPIT, Harbinger, mcp-snitch, Sketchy |
| [fuzzing-research-2025-2026.md](./fuzzing-research-2025-2026.md) | Academic fuzzing frontier (USENIX '25 + NDSS '26) | IDFuzz, G²FUZZ, Lyso, DUMPLING, Fuzzilicon, IoTBec + 4 more |
| [teampcp-postmortem.md](./teampcp-postmortem.md) | TeamPCP incident post-mortem & lessons learned | Attack chain, detection gaps, SmokedMeat/Plumber/Brutus response, forecast |
| [firmware-memory-forensics.md](./firmware-memory-forensics.md) | UEFI firmware parsing + Linux memory forensics | CERT UEFI Parser, mquire |
| [defensive-ops.md](./defensive-ops.md) | Host firewall + OSS SOAR | Little Snitch for Linux, Allama |
| [secret-scanning.md](./secret-scanning.md) | Secret scanning with CEL + BPE naturalness | Betterleaks (vs Gitleaks / TruffleHog) |
| [c2-frameworks.md](./c2-frameworks.md) | C2 / red-team framework landscape comparison | Sliver, Mythic, Empire 6.0, Havoc, C4, SmokedMeat, Beaconator (+ Cobalt Strike for ref) |
| [perimeter-stack.md](./perimeter-stack.md) | **Perimeter stack landscape** — chain coverage, ProjectDiscovery dominance, Nuclei templates, recon comparison | All 16 perimeter submodules + adjacent appsec (Vespasian/Hadrian/Brutus) |
| [code/](./code/) | **Code-level analyses (33 reports + cross-cutting [`_landscape.md`](./code/_landscape.md))** — architecture + novel implementation details from actual source, one per tool, every claim grounded in `path:LINE` references | 33 of the ~40 mirrored submodules across all categories. The landscape report adds analytics: language distribution, architectural-pattern heatmap (12 patterns), storage backends, codebase size, test depth, license posture, and the code-quality issues surfaced during review. |
| [landscape-analysis.md](./landscape-analysis.md) | **Cross-cutting trend analysis + forward predictions** (charts + mermaid) | All tools, aggregated |

## Cross-cutting observations

Five themes show up repeatedly when you read these codebases together:

1. **MCP wrappers are the new "give me a CLI"** — Trivy, Seclab Taskflow Agent, Hadrian's planner, and now `cloud-audit` all ship MCP servers or MCP-callable surfaces. Wrapping an existing CLI in an MCP server is a *one-week* effort that turns a tool into an agent-callable capability. Expect Plumber, Betterleaks, Brutus, and mquire MCP wrappers within Q3 2026.
2. **The "agentic framework + YAML grammar" pattern is converging** — Seclab Taskflow Agent's grammar (taskflow / personality / toolbox / prompt / model_config), Hadrian's template grammar (endpoint_selector / role_selector / http / detection / test_phases), Allama's visual workflow builder, and Plumber's Rego policies are independent implementations of the same idea: declarative configuration that LLM agents or policy engines consume as orchestration scaffolding. This is how "agents" become operationalizable in security tooling.
3. **The vendor-OSS pipeline has accelerated** — Praetorian (Vespasian / Hadrian / Julius / Brutus), Trail of Bits (Buttercup / Trailmark / CoBRA / mquire / Ruzzy), Doyensec (SafeUpdater / maSSO), GitHub Security Lab (Taskflow Agent), Boost Security Labs (poutine / SmokedMeat), Aikido (Betterleaks), CMU/SEI CERT (UEFI Parser), Objective Development (Little Snitch for Linux) all run a *post-engagement → OSS release* (or *commercial-product OSS-component*) pipeline. Tools used internally are now reaching public release in months, not years.
4. **CEL is winning the policy-expression-language war** — Spotter (K8s scanning), Plumber (CI/CD compliance), Betterleaks (secret-scanner filters and validators), Kubernetes admission, Envoy, Tekton. The skill is reusable across security-adjacent tools; worth investing in.
5. **The TeamPCP incident (March 2026) reshaped priorities** — SmokedMeat, Plumber, and Brutus all appeared inside three months of TeamPCP. CI/CD pipeline compromise is no longer a niche risk; it is a tier-1 risk and the OSS tooling shipped accordingly.

The reports below each pick *one specific innovation* per tool and explain why it matters — read with that lens.
