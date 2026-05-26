# LLM red-team & agent-abuse — landscape overview

The "agentic security" wave that the [README](../README.md) flags as theme #2 of the year produced two distinct outputs: a **converging tool stack** for LLM red-teaming (Promptfoo, GARAK, PyRIT, DeepTeam) and a **research wave** documenting how enterprise AI agents — Bedrock, Copilot, ChatGPT plugins, MCP-connected tools — get exploited in practice. This report covers both.

Unlike most categories in this brief, this one has **no submodule** — the tools are too numerous and the research too fast-moving to mirror. The meaningful comparison is about positioning: which tool covers which attack surface, and how the attack research maps to the tool capabilities. For the per-conference raw notes, see [`defcon-33.md`](../conferences/defcon-33.md), [`black-hat-usa-2025.md`](../conferences/black-hat-usa-2025.md), [`black-hat-europe-2025.md`](../conferences/black-hat-europe-2025.md), and [`fwd-cloudsec-2025.md`](../conferences/fwd-cloudsec-2025.md).

The category is **Mixed (2 offensive, 2 defensive)** per the [landscape analysis](./landscape-analysis.md) offense/defense balance — one of the few categories where attack and defense tooling ship concurrently from different vendors.

---

## The converging de-facto stack

Four tools have consolidated as the standard LLM red-team toolkit across conference Arsenal floors (BH USA 2025, DEF CON 33) and enterprise adoption:

| | Promptfoo | GARAK (NVIDIA) | PyRIT (Microsoft) | DeepTeam |
|---|---|---|---|---|
| Repo | `promptfoo/promptfoo` | `NVIDIA/garak` | `Azure/PyRIT` | `confident-ai/deepteam` |
| Side | Offensive (scanner) | Offensive (scanner) | Offensive (toolkit) | Defensive (eval framework) |
| Primary surface | LLM apps, MCP servers, agents, RAG pipelines | LLM models: data leakage, misinformation, hallucination, toxicity | AI systems broadly: prompt injection, jailbreak, data extraction | LLM systems: red-team eval with metric-driven pass/fail |
| Language | TypeScript (CLI + web UI) | Python | Python | Python |
| License | MIT | Apache-2.0 | MIT | Apache-2.0 |
| Adoption signal | 100K+ devs; most-cited LLM scanner in 2025 | NVIDIA backing; broadest vuln taxonomy | Microsoft backing; integrated into Azure AI ecosystem | Companion to DeepEval (the pytest-for-LLMs project) |
| Standout | MCP-server scanning; agent workflow attack graphs; CI/CD integration (GitHub Actions, GitLab CI) | Auto-attack generation; plugin architecture for custom probes; 40+ probe families covering OWASP LLM Top 10 | Orchestrated multi-turn attack chains; converter architecture (Base64, ROT13, Unicode, image-based) for payload transformation | Metric-anchored red-team: toxicity, bias, hallucination, PII leakage scored against configurable thresholds |
| Conference presence | BH USA 2025 Arsenal, DEF CON 33 | BH USA 2025 Arsenal, DEF CON 33 | BH USA 2025 Arsenal | BH USA 2025 Arsenal |

### How they relate

The four are not competitors in the usual sense — they cover overlapping but distinct slices:

1. **Promptfoo** is the **application-layer scanner**. It treats the LLM app (not the model) as the target: test your prompt templates, your RAG pipeline, your MCP tool integrations, your agent orchestration. The 2025-2026 addition of MCP-server scanning is its sharpest differentiator — no other tool in the stack natively understands MCP tool definitions and can generate injection payloads targeting tool-call schemas.

2. **GARAK** is the **model-layer scanner**. It treats the model itself as the target: probe for training-data leakage, test guardrail bypass, measure misinformation generation rates. The auto-attack generator (which mutates seed prompts via LLM-driven rewriting) is the capability that separates it from static prompt-list tools. 40+ probe families organized by OWASP LLM Top 10 categories.

3. **PyRIT** is the **orchestration toolkit**. It does not ship a fixed set of probes — instead it provides the plumbing for multi-turn, multi-converter attack chains. The converter architecture (Base64, ROT13, Unicode homoglyph, image-based prompt injection, Morse code, Caesar cipher) is the part that matters: it transforms a single seed payload into dozens of encoding variants and tests each. PyRIT is what you use when you need to build a custom attack campaign against a specific system, not run a generic scan.

4. **DeepTeam** is the **eval-framework-with-red-team-built-in**. It extends the DeepEval testing library with adversarial test cases — the same `pytest`-style interface, but the test assertions are "this LLM system should not leak PII under these 50 attack prompts" instead of "this response should be relevant." The metric-anchored approach (toxicity score < 0.3, bias score < 0.2, etc.) makes it the most CI/CD-friendly of the four.

The operational combination for a 2026 team: **GARAK for model-level baseline** (run against your model endpoint before deployment), **Promptfoo for app-level scanning** (run against your RAG/agent/MCP stack in staging), **PyRIT for bespoke attack campaigns** (when the automated scanners find something interesting and you need to go deeper), **DeepTeam for regression** (run in CI to catch regressions against known attack patterns).

---

## Specialized tools (new 2025-2026)

Six tools that ship alongside the core stack, each targeting a narrower attack surface:

### promptmap2 (Utku Sen)

**Repo:** `utkusen/promptmap` — DEF CON 33 Demo Labs.

Automated prompt-injection scanner for custom LLM applications. Sends crafted injection payloads to the target LLM app and detects whether the injection succeeded by analyzing the response. The tool's value is its focus on **custom enterprise LLM apps** (not models in isolation) — the same apps that Promptfoo scans, but with a lighter-weight, single-purpose approach. It's the `sqlmap` analog for prompt injection: point it at a URL, let it enumerate injection vectors.

### MPIT — Matrix Prompt Injection Tool (Sh1n0g1)

**Repo:** `Sh1n0g1/mpit` — DEF CON 33 Demo Labs.

Genetic-algorithm-driven prompt-injection payload optimizer. MPIT takes a seed prompt-injection payload and evolves it through mutation and crossover to maximize injection success rate against a target LLM. The genetic-algorithm approach is the differentiator — instead of using a fixed payload list (like most injection scanners), MPIT adapts payloads to the specific model and guardrail configuration it's targeting. The result is payloads optimized to bypass the exact defenses the target has deployed.

### Harbinger (Mandiant)

Black Hat Europe 2025 Arsenal. The first **major-vendor OSS AI red-team release** — Mandiant (Google Cloud) releasing a purpose-built AI threat-modeling and red-team tool. Harbinger fills the gap between the model-testing tools (GARAK, PyRIT) and the application-testing tools (Promptfoo) by providing a **threat-modeling framework** specifically for AI systems. The vendor provenance matters: Mandiant's incident-response data informs the threat models, making them empirically grounded rather than theoretical.

See [`black-hat-europe-2025.md`](../conferences/black-hat-europe-2025.md) for conference context.

### mcp-snitch (Adversis)

**Repo:** `Adversis/mcp-snitch` — DEF CON 33 Cloud Village.

macOS MCP-server traffic interceptor and audit logger. Sits between the MCP client (Claude Desktop, Cursor, etc.) and the MCP server, logging every tool call, every parameter, and every response. The tool exists because MCP servers run with the user's full permissions and there is **no native audit log** in the MCP protocol — mcp-snitch creates one.

The strategic relevance: MCP wrapping is the 2026 distribution pattern for security tools (Trivy MCP, cloud-audit MCP, etc. — see [`cloud-posture.md`](./cloud-posture.md)). Every MCP server is a new trusted-code-execution surface. mcp-snitch is the first tool that makes that surface observable. See the Doyensec MCP auth analysis below for the protocol-level vulnerability context.

### Sketchy (Adversis)

**Repo:** `Adversis/sketchy` — DEF CON 33 Cloud Village.

Cross-platform behavioral scanner with 25+ suspicious-pattern detections. Sketchy monitors running processes and system behavior for patterns associated with malicious activity — including patterns specific to AI agent abuse (unexpected network connections from MCP servers, unauthorized file access by agent processes, data exfiltration patterns). It is the **runtime counterpart** to mcp-snitch's network-layer interception: mcp-snitch logs what MCP servers say, Sketchy logs what they do.

### Mindgard

Referenced in the [README](../README.md) as part of the converging LLM red-team stack. Commercial platform with an OSS community tier for AI security testing. Positioned as an enterprise-grade complement to the Promptfoo/GARAK/PyRIT trio, with managed scan orchestration, compliance reporting, and model-vulnerability database. No detailed repo link available at time of writing.

---

## Agent-abuse attack research

The research side of this category is where the highest-impact findings live. The tools above test for known vulnerability classes; the research below defines the vulnerability classes.

### The three canonical attack vectors (2025-2026)

These three attack chains, documented across BH USA, DEF CON, and fwd:cloudsec, define the current agent-abuse threat model:

**1. Enterprise-agent 0-click exploitation — AgentFlayer (Zenity)**

Black Hat USA 2025. The most-discussed agent-attack research of 2025.

Zenity demonstrated 0-click exploit chains against **ChatGPT, Gemini, and Microsoft Copilot** enterprise agents. The attacks exploit the trust boundary between the agent's system prompt and user-supplied content — specifically, content that arrives via enterprise integrations (email, calendar, documents) rather than direct user input. The 0-click designation is accurate: the victim does not need to interact with the attacker's payload; the agent processes it automatically as part of its normal workflow.

The implication for defense: any enterprise AI agent with access to user-controlled data sources (email, SharePoint, Slack, Jira) is a prompt-injection target, and the injection happens through the data plane, not the control plane. See [`black-hat-usa-2025.md`](../conferences/black-hat-usa-2025.md).

**2. Managed-agent template takeover — Bedrock Agent exploitation (fwd:cloudsec)**

"Breaking AI Agents: Exploiting Managed Prompt Templates to Take Over Amazon Bedrock Agents" (Jay Chen, Royce Lu) — fwd:cloudsec 2025.

Demonstrated that Amazon Bedrock's managed prompt templates — the system prompts that define agent behavior — can be hijacked through prompt injection in the agent's data sources. The attack chain: inject into a document that the Bedrock agent retrieves via its knowledge base, override the system prompt, redirect the agent's actions. The result is full agent takeover — the attacker controls what the agent does with the user's AWS permissions.

This is a cloud-provider-specific instance of the general "indirect prompt injection" pattern, but the Bedrock-specific detail matters: the managed template architecture creates a **single point of override** that, once compromised, gives the attacker control over the agent's entire tool-call surface. See [`fwd-cloudsec-2025.md`](../conferences/fwd-cloudsec-2025.md).

**3. MCP-server interception and tool poisoning**

Documented across multiple talks and tools: mcp-snitch (DEF CON 33), Doyensec "The MCP AuthN/Z Nightmare" (March 2026), and the broader MCP security discussion at RSA 2026.

The MCP protocol, as shipped in 2025-2026, has **no authentication or authorization specification**. Any process that can connect to the MCP server's transport (stdio, SSE, HTTP) can invoke any tool the server exposes. The Doyensec analysis (March 2026) documented three concrete vector classes:
- **Tool poisoning:** a malicious MCP server registers tools with names and descriptions designed to trick the LLM into calling them instead of legitimate tools.
- **Prompt injection via tool responses:** a compromised MCP server returns tool results containing prompt-injection payloads that redirect the LLM's subsequent behavior.
- **Command injection via tool parameters:** the MCP server passes user-controlled input to shell commands without sanitization.

mcp-snitch makes the first two observable; Sketchy detects behavioral signatures of the third.

### Additional high-impact research

**"From Prompts to Pwns: Exploiting and Securing AI Agents"** — Black Hat USA 2025. End-to-end LLM/agent attack lifecycle talk that became the de-facto reference for agent threat modeling. Maps the full chain from initial prompt injection through privilege escalation to data exfiltration, with practical examples at each stage. See [`black-hat-usa-2025.md`](../conferences/black-hat-usa-2025.md).

**"Double Agents: Exposing Hidden Threats in AI Agent Platforms"** — fwd:cloudsec 2025. Broader survey of attack patterns on agent platforms, covering multi-agent architectures where one compromised agent can influence others through shared context or tool-call chains. See [`fwd-cloudsec-2025.md`](../conferences/fwd-cloudsec-2025.md).

**"Bypassing AI Security Controls with Prompt Formatting"** (Nathan Kirk) — fwd:cloudsec 2025. Demonstrated that formatting-level manipulations (Unicode directionality overrides, zero-width characters, markdown injection, HTML entities) can bypass LLM security classifiers that operate on semantic content but not on formatting. The PyRIT converter architecture is the tool-side response to this class of attack.

**CVE-2026-25592 + CVE-2026-26030 — Microsoft Semantic Kernel RCE** — Disclosed May 2026. Prompt injection in Microsoft Semantic Kernel leading to **host-level remote code execution**. The chain: attacker-controlled input reaches the Semantic Kernel agent, prompt injection redirects the agent to call a code-execution tool (Python plugin or shell plugin), the tool executes attacker-controlled code on the host. One of the most important AI-security disclosures of the year because it demonstrates the **prompt-injection-to-RCE pipeline** that the "From Prompts to Pwns" talk described theoretically — now confirmed in a production Microsoft framework with CVE assignments.

**ToxicSkills (Snyk)** — First large-scale survey of malicious AI agent skills: 1,467 malicious payloads and prompt-injection vulnerabilities found in agent skill registries (analogous to malicious packages in npm/PyPI, but for agent tool definitions). ToxicSkills documents the **supply-chain attack surface for AI agents**: if your agent loads skills from a registry, those skills can contain prompt-injection payloads that activate when the agent invokes them. This is the agent equivalent of dependency confusion.

**"The MCP AuthN/Z Nightmare" (Doyensec, March 2026)** — Comprehensive auth/authZ analysis of the Model Context Protocol. Documents that MCP as specified has no authentication, no authorization, no tool-call signing, and no transport-layer security requirements. The analysis covers tool poisoning, prompt injection through tool responses, command injection through tool parameters, and cross-server confusion attacks. The most thorough protocol-level vulnerability assessment of MCP published to date.

**"Bypassing LLM Supervisor Agents Through Indirect Prompt Injection" (Praetorian, April 2026)** — Demonstrates that the "supervisor agent" pattern (a meta-agent that monitors and constrains other agents) can itself be bypassed through indirect prompt injection in the supervised agents' outputs. The implication: adding a supervisor agent does not add a security boundary; it adds another prompt-injection target.

**"Which Came First: The System Prompt, or the RCE?" (Praetorian, March 2026)** — Agent-to-RCE chain analysis. Documents the pattern where an agent's system prompt grants tool-call permissions that, combined with prompt injection, produce remote code execution. The analysis covers multiple agent frameworks and identifies the common architectural flaw: treating the system prompt as both a capability specification and a security boundary.

---

## Agent-abuse attack taxonomy

Synthesizing the research above into an operational taxonomy:

| Vector | Entry point | Pivot | Impact | Example |
|---|---|---|---|---|
| Direct prompt injection | User input to agent | Override system prompt | Agent behavior hijack | Basic jailbreak |
| Indirect prompt injection (data plane) | Document, email, calendar event, DB record | Agent retrieves poisoned content | 0-click agent takeover | AgentFlayer (Copilot, Gemini, ChatGPT) |
| Managed template override | Cloud-provider prompt template (Bedrock) | Inject into knowledge-base document | Full agent takeover with cloud permissions | Bedrock Agent takeover (fwd:cloudsec) |
| MCP tool poisoning | Malicious MCP server registration | LLM selects attacker's tool over legitimate tool | Arbitrary tool execution | Doyensec MCP analysis |
| MCP response injection | Compromised MCP server response | Injected prompt in tool output | Redirect subsequent LLM actions | Doyensec MCP analysis |
| Skill/plugin supply chain | Malicious skill in agent registry | Agent loads and invokes malicious skill | Prompt injection + data exfil | ToxicSkills (Snyk) |
| Prompt formatting bypass | Unicode, zero-width chars, markdown | Evade security classifier | Bypass guardrails | Nathan Kirk (fwd:cloudsec) |
| Supervisor bypass | Indirect injection in supervised agent output | Supervisor processes poisoned context | Defeat monitoring/guardrail layer | Praetorian supervisor bypass |
| Agent-to-RCE | Prompt injection + code-execution tool | System prompt grants shell/code tool access | Host RCE | CVE-2026-25592, Praetorian system-prompt analysis |

The common thread: **every trust boundary in the agent architecture is a prompt-injection surface**, and prompt injection is not a bug class with a single fix — it is a fundamental property of systems where untrusted data and instructions share the same channel.

---

## Tool-to-research coverage map

Which tools can test for which research-documented attack classes:

| Attack class | Promptfoo | GARAK | PyRIT | DeepTeam | promptmap2 | MPIT | mcp-snitch | Sketchy |
|---|---|---|---|---|---|---|---|---|
| Direct prompt injection | ● | ● | ● | ● | ● | ● | · | · |
| Indirect prompt injection | ● | ◐ | ● | ◐ | ◐ | · | · | · |
| MCP tool poisoning | ● | · | · | · | · | · | ● (detect) | · |
| MCP response injection | ● | · | · | · | · | · | ● (detect) | · |
| Data leakage / extraction | ◐ | ● | ● | ● | · | · | · | · |
| Guardrail bypass | ● | ● | ● | ● | ● | ● | · | · |
| Encoding/formatting bypass | ◐ | ◐ | ● | · | · | ● | · | · |
| Agent behavioral anomaly | · | · | · | · | · | · | ◐ | ● |
| Agent-to-RCE chain | ◐ | · | ◐ | · | · | · | · | ● (detect) |

`●` = primary coverage, `◐` = partial, `·` = not covered.

The gap in the matrix is telling: **no single tool covers the full attack taxonomy**. The closest to full coverage is the Promptfoo + mcp-snitch + Sketchy combination (application-layer scanning + network-layer MCP audit + runtime behavioral detection), but even that stack does not cover model-level data-leakage testing (GARAK's domain) or custom multi-turn attack orchestration (PyRIT's domain).

---

## Strategic recommendations

**1. Treat the four-tool stack as a baseline, not a menu.**

Promptfoo + GARAK + PyRIT + DeepTeam cover different layers. Running only one is like running only SAST without DAST — you will miss entire vulnerability classes. The minimum viable LLM security pipeline is: GARAK against the model endpoint (pre-deployment), Promptfoo against the application (staging), DeepTeam in CI (regression). PyRIT for deep-dive campaigns when automated scans surface anomalies.

**2. MCP is the new attack surface. Instrument it now.**

MCP wrapping is the 2026 distribution pattern for security tools ([Trivy MCP](../sources/appsec/trivy-mcp), [cloud-audit MCP](./cloud-posture.md)). Every MCP server your agent connects to is a trusted-code-execution surface with no native audit log and no protocol-level authentication. Deploy mcp-snitch (macOS) or an equivalent interceptor on every machine running MCP-connected agents. Treat MCP server additions the same way you treat new dependencies: review, pin, monitor.

**3. The Semantic Kernel CVEs are the warning shot for agent-to-RCE.**

CVE-2026-25592 and CVE-2026-26030 confirmed that prompt-injection-to-host-RCE is not theoretical. Any agent framework that grants code-execution tools (Python, shell, SQL) to an LLM that processes untrusted input has this vulnerability class. Audit your agent architectures for this pattern. The Praetorian "system prompt or RCE" analysis provides the methodology.

**4. Supervisor agents are not security boundaries.**

Praetorian's April 2026 research showed that LLM-based supervisor agents can be bypassed through the same indirect-prompt-injection techniques that work on the agents they supervise. Do not treat a supervisor agent as a guardrail substitute. Defense-in-depth for agents means: input sanitization before the LLM, output validation after the LLM, tool-call allowlisting at the framework level, and runtime behavioral monitoring (Sketchy) — not another LLM in the loop.

**5. Agent skill registries are the next supply-chain attack surface.**

ToxicSkills documented 1,467 malicious payloads in agent skill registries. This is the agent equivalent of the npm/PyPI malicious-package problem, but earlier in its lifecycle — meaning the defenses (lockfiles, signature verification, provenance attestation) that took a decade to build for package managers do not yet exist for agent skills. Treat agent skill additions with the same rigor you apply to dependency additions: review the skill definition, pin the version, monitor for changes.

**6. Budget for this to get worse before it gets better.**

The agent-abuse research published in 2025-2026 documents fundamental architectural problems (shared instruction/data channel, no authentication in MCP, trust-by-default in agent frameworks) that will take years to address at the protocol and framework level. In the meantime, the attack surface is expanding faster than the defense surface. The tools documented here are the best available mitigations, but they are mitigations — not solutions.

---

## Where the category is going

1. **Promptfoo will become the default CI/CD gate for LLM apps.** The same way linters gate code and SAST gates builds, Promptfoo (or a Promptfoo-shaped tool) will gate LLM application deployments. The GitHub Actions / GitLab CI integration is already there; adoption will follow the same curve as Snyk/Trivy adoption for container scanning.

2. **MCP authentication will ship, but slowly.** The Doyensec analysis and the mcp-snitch visibility gap will force the MCP specification to add auth. Expect a draft authentication extension by late 2026 and patchy adoption through 2027. Until then, mcp-snitch-style interceptors are the only visibility layer.

3. **GARAK's auto-attack generator will get competitors.** The genetic-algorithm approach (MPIT) and the LLM-rewriting approach (GARAK) are two instances of the same idea: adaptive payload generation. Expect PyRIT and Promptfoo to ship equivalent capabilities, and expect a standalone OSS "LLM fuzzer" project to emerge by Q4 2026.

4. **Agent-to-RCE will become a named vulnerability class.** The Semantic Kernel CVEs, the Praetorian research, and the inevitable next disclosure will establish "prompt injection to code execution" as a tracked CWE or OWASP category. The "From Prompts to Pwns" talk is the precursor framing.

5. **The tool stack will consolidate around MCP.** Promptfoo already scans MCP servers. GARAK and PyRIT will add MCP-aware probes. Harbinger (Mandiant) will likely ship MCP threat models. Within 12 months, "can it test MCP servers?" will be the qualifying question for LLM red-team tools, the same way "can it scan containers?" qualified SAST tools in 2020.

6. **Enterprise agent platforms will add audit logging.** The mcp-snitch gap — "there is no native audit log" — is the kind of missing primitive that gets shipped fast once a sufficiently embarrassing breach demonstrates the need. Expect Microsoft (Copilot), Google (Gemini), and Anthropic (Claude) to add agent-action audit logs by mid-2027. Amazon Bedrock's agent logging (flagged as inadequate in the fwd:cloudsec "Challenges around AI as a Service logging" talk) will improve first because the gap is already publicly documented.
