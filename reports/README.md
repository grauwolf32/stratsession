# Per-class deep-dive reports

In-depth exploration of the 17 AppSec submodules under [`../sources/appsec/`](../sources/appsec/), focused on **what each tool actually does that's new or unusual** — not feature-list marketing. Where multiple tools share a class, they are compared side-by-side.

| Report | Class | Tools compared |
|---|---|---|
| [fuzzing.md](./fuzzing.md) | Fuzzing engines & frameworks | AFL++, LibAFL, Ruzzy |
| [ai-vuln-research.md](./ai-vuln-research.md) | AI-driven vulnerability discovery | Buttercup, Seclab Taskflow Agent |
| [waf.md](./waf.md) | Web Application Firewalls | Coraza (engine), Core Rule Set (ruleset) |
| [scanners.md](./scanners.md) | Vulnerability scanners & patch analyzers | Trivy, Trivy MCP, Nettacker, PatchLeaks |
| [api-security.md](./api-security.md) | API discovery + authorization testing | Vespasian, Hadrian |
| [vulnmgmt-sbom.md](./vulnmgmt-sbom.md) | Vulnerability management & SBOM | DefectDojo, Sunshine |
| [reference-design.md](./reference-design.md) | Reference designs & training labs | SafeUpdater (Electron), DVBE (Damn Vulnerable Browser Extension) |

## Cross-cutting observations

Three themes show up repeatedly when you read these 17 codebases together:

1. **MCP wrappers are the new "give me a CLI"** — Trivy, Seclab Taskflow Agent, and Hadrian's planner all ship MCP servers or MCP-callable surfaces. Wrapping an existing CLI in an MCP server is now a *one-week* effort that turns a tool into an agent-callable capability. Trivy went from CLI to MCP server in a tagged plugin; Hadrian uses MCP toolboxes from the start.
2. **The "agentic framework + YAML grammar" pattern is converging** — Seclab Taskflow Agent's grammar (taskflow / personality / toolbox / prompt / model_config files) and Hadrian's template grammar (endpoint_selector / role_selector / http / detection / test_phases) are independent implementations of nearly the same idea: declarative YAML that the LLM consumes as both prompt and orchestration scaffolding. This is the operationalization of "agents" in security tooling.
3. **The vendor-OSS pipeline has accelerated** — Praetorian (Vespasian/Hadrian/Julius), Trail of Bits (Buttercup/Trailmark/CoBRA/mquire/Ruzzy), Doyensec (SafeUpdater/maSSO), and GitHub Security Lab (Taskflow Agent) all run a *post-engagement → OSS release* pipeline. Tools used internally by consultants are now reaching public release in months, not years. The repos under `sources/appsec/` reflect this: ~half were first-released or majorly rewritten inside the past 12 months.

The seven reports below each pick *one specific innovation* per tool and explain why it matters — read with that lens.
