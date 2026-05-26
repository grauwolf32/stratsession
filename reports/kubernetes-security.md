# Kubernetes / container security — detection, posture, admission

The Kubernetes security tooling surface in 2025-2026 split cleanly into two layers: a **detection layer** that converged around three CNCF/eBPF projects (Falco + StratoShark, Tetragon, Tracee), and a **posture/admission layer** that fragmented across CEL-based scanners, entitlement analyzers, admission engines, and image patchers. Neither layer is self-sufficient; a production stack needs both. A third category — training/red-team manifests — rounds out the picture.

This report covers tools surfaced at **KubeCon NA 2025** (Kyverno, Kubewarden, Copacetic, Falco + StratoShark) and **DEF CON 33** (Spotter, KIEMPossible, HoneyBee), plus the eBPF detection stack already documented across [`defensive-ops.md`](./defensive-ops.md) and [`TOOLS.md`](../TOOLS.md). Unlike the CI/CD and cloud-posture reports, none of these tools exist as git submodules here — this is a landscape comparison, similar to [`c2-frameworks.md`](./c2-frameworks.md).

---

## Detection layer — eBPF runtime security

All three detection tools instrument the Linux kernel via eBPF. The meaningful differences are in *what they instrument*, *how they express policy*, and *what they do when a rule fires*.

| | Falco + StratoShark | Tetragon | Tracee |
|---|---|---|---|
| Maintainer | Sysdig / CNCF (graduated) | Isovalent / Cilium (CNCF incubating) | Aqua Security |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Primary hook | Kernel module + eBPF (syscall tap) | eBPF (kprobes, tracepoints, LSM hooks) | eBPF (kprobes, tracepoints, LSM hooks) |
| Rule language | YAML (Falco rules DSL) | TracingPolicy CRD (YAML + selectors) | Rego + YAML signatures |
| Enforcement (kill/block) | No (detect-only; pairs with response engines) | Yes (SIGKILL inline via LSM) | Yes (via signatures; also detect-only mode) |
| Network visibility | Limited (syscall-level) | Deep (Cilium network flow integration) | Moderate (network event tracing) |
| Forensic capture | **StratoShark** (Wireshark-style syscall replay) | No built-in (export to SIEM) | No built-in (export to SIEM) |
| Kubernetes context | Pod/namespace metadata enrichment | Native CRD, namespace-scoped policies | Pod/namespace metadata enrichment |
| Community rules | 100+ upstream rules | Growing policy library | 60+ built-in signatures |
| Best at | Broad syscall detection + post-incident forensics | Kernel-level enforcement + network-aware detection | Detect-and-respond with Rego flexibility |

### Falco + StratoShark — detection + forensic replay

**Falco** (`falcosecurity/falco`) is the CNCF-graduated runtime detection engine. It watches syscalls (via kernel module or eBPF probe), evaluates them against YAML rules, and emits alerts. The rule language is mature and well-documented; the community rule set covers container escapes, shell-in-container, sensitive file reads, crypto-mining patterns, and lateral movement.

What changed in 2025: **StratoShark** (`sysdiglabs/stratoshark`). Gerald Combs (Wireshark's creator) presented it at [KubeCon NA 2025](../conferences/kubecon-na-2025.md). StratoShark is a Wireshark-style forensic interface for syscall captures. The workflow:

1. Falco rule fires (e.g., "shell spawned in container").
2. Targeted syscall capture begins on that container/pod.
3. Capture file is analyzable in StratoShark with the same filter/dissector model Wireshark uses for network packets.

This closes a gap that has existed since Falco's inception: Falco tells you *that* something happened, but the alert alone rarely carries enough context for IR. StratoShark gives the forensic investigator the full syscall-level replay — file operations, network calls, process trees — in a familiar interface. The pairing is the first time a CNCF detection project has shipped a forensic-grade capture companion.

**When to pick Falco + StratoShark:** When the primary need is detection breadth + post-incident forensic analysis, and enforcement is handled elsewhere (e.g., by Kubernetes NetworkPolicy, OPA/Kyverno admission, or a service mesh).

### Tetragon — kernel enforcement + network-aware detection

**Tetragon** (`cilium/tetragon`) is Isovalent's eBPF security observability and enforcement engine. It hooks deeper than Falco — kprobes, tracepoints, and LSM hooks rather than just the syscall boundary — and can **kill processes inline** (SIGKILL at the LSM hook, before the syscall completes). This is the critical differentiator: Tetragon doesn't just detect; it blocks.

The policy model is Kubernetes-native: `TracingPolicy` CRDs deployed per-namespace or cluster-wide. Policies can match on binary path, namespace, capability, argument values, and kernel function. The Cilium integration gives Tetragon network-level context that neither Falco nor Tracee have natively — you can write a single policy that correlates a process exec with the network flow it generates.

**When to pick Tetragon:** When you need inline enforcement (kill on violation), when you're already running Cilium as your CNI, or when network-flow-aware detection is a requirement.

### Tracee — Rego-based detect-and-respond

**Tracee** (`aquasecurity/tracee`) is Aqua's eBPF runtime security tool. Its distinguishing feature is the Rego-based signature engine: detection rules are written in the same policy language used by OPA/Gatekeeper. For teams already invested in the OPA ecosystem, this means detection rules and admission policies share a language.

Tracee also supports built-in YAML signatures (60+) and can operate in enforcement mode (block via LSM). It's the middle ground between Falco's pure-detection model and Tetragon's kernel-enforcement-first approach.

**When to pick Tracee:** When Rego expertise already exists on the team (OPA/Gatekeeper users), or when you want a single vendor (Aqua) covering both runtime detection (Tracee) and vulnerability scanning (Trivy).

### Detection layer: strategic read

The three tools are more complementary than competitive. A defensible stack looks like:

```
Detection (broad)          Falco          — catches the most categories of suspicious activity
Enforcement (inline)       Tetragon       — kills processes before damage completes
Forensics (post-incident)  StratoShark    — replay the syscall capture for IR
Network correlation        Tetragon/Cilium — flow-level visibility
```

Running all three is overkill for most organizations. The practical choice:

- **Cilium shops:** Tetragon (already there) + Falco for the broader rule community + StratoShark for IR.
- **Non-Cilium shops:** Falco + StratoShark as the primary detection/forensics pair. Add Tracee if Rego alignment with existing OPA policies matters.

This stack maps to the eBPF defensive layer documented in [`defensive-ops.md`](./defensive-ops.md) lines 68-83, where these three tools plus Little Snitch for Linux form the "2026 complete Linux defensive stack."

---

## Posture / admission layer

The posture layer is fragmented. Five tools, five different approaches, and no single winner. The common thread: **CEL is becoming the default policy expression language**, used by Spotter, Kyverno (new policy types), Kubewarden (alongside Rego and Wasm), Kubernetes ValidatingAdmissionPolicy, Envoy, and Tekton.

### Side-by-side comparison

| | Spotter | Kyverno | Kubewarden | Copacetic | KIEMPossible |
|---|---|---|---|---|---|
| Function | Scanner (offline + live) | Admission controller + policy engine | Admission controller | Image patcher | Entitlement analyzer |
| Author | Madhu Akula | Nirmata / CNCF | SUSE / CNCF | Microsoft / CNCF | Palo Alto Networks |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Policy language | CEL | CEL (new) + YAML | Rego + CEL + Wasm | N/A (scanner output) | N/A (analysis tool) |
| Operates on | Manifests + live clusters | Live admission requests | Live admission requests | Container images | Live RBAC + usage data |
| Coverage framework | OWASP K8s Top 10, CIS, NSA/CISA | Custom policies (any) | Custom policies (any) | CVE patches | K8s RBAC permissions |
| Release surface | DEF CON 33 | KubeCon NA 2025 | KubeCon NA 2025 | KubeCon NA 2025 | DEF CON 33 |
| New in 2025 | Entire tool | 5 new policy resource types | Unified engine (Rego + CEL + Wasm) | Image-patching workflow | Entire tool |

### Spotter — CEL-based Kubernetes scanner

**Repo:** `madhuakula/spotter` · License: Apache-2.0 · Go. Presented at [DEF CON 33](../conferences/defcon-33.md) Cloud Village and Demo Labs.

Spotter is a Kubernetes security scanner that evaluates manifests (YAML files, Helm charts, live cluster resources) against CEL-based rules covering OWASP Kubernetes Top 10, CIS Kubernetes Benchmark, and NSA/CISA Kubernetes Hardening Guide.

What makes it distinct from kube-bench or Polaris:

1. **CEL rules, not Rego or custom DSL.** Rules are written in the same CEL that Kubernetes itself uses for ValidatingAdmissionPolicy. The skill transfers directly.
2. **Offline + live.** Scan manifests in CI before deployment, scan running clusters after. Same rule set, both modes.
3. **Framework coverage in one tool.** OWASP K8s Top 10, CIS, and NSA/CISA under one scanner rather than requiring three separate tools (kube-bench for CIS, manual checks for NSA/CISA, nothing standardized for OWASP K8s).

**Positioning:** Spotter is the *scanner*; Kyverno/Kubewarden are the *enforcers*. Spotter finds the problem in CI or on a schedule. Kyverno/Kubewarden prevent the problem at admission time. They are complementary.

### Kyverno — five new policy resource types

**Repo:** `kyverno/kyverno` · License: Apache-2.0 · Go. Demoed at [KubeCon NA 2025](../conferences/kubecon-na-2025.md).

Kyverno's 2025 release shipped five new policy resource types that materially expand what can be expressed in a single policy engine:

| Policy type | What it does | Previously required |
|---|---|---|
| **ValidatingPolicy** | CEL-based validation (replaces JMESPath) | ValidatingAdmissionPolicy (K8s built-in) or OPA |
| **ImageValidatingPolicy** | Image signature + attestation verification | Cosign + custom admission webhook |
| **MutatingPolicy** | CEL-based mutation of incoming resources | MutatingAdmissionWebhook + custom code |
| **GeneratingPolicy** | Auto-create dependent resources on admission | Custom controller |
| **DeletingPolicy** | Auto-delete resources matching conditions | Custom controller or CronJob |

The strategic significance: Kyverno is now a **single admission controller that handles validation, mutation, generation, deletion, and image verification** — a scope that previously required 3-4 separate tools. The shift from JMESPath to CEL aligns Kyverno with the broader Kubernetes ecosystem direction.

### Kubewarden — unified Rego + CEL + Wasm engine

**Repo:** `kubewarden/kubewarden-controller` · License: Apache-2.0 · Rust + Go. Presented at [KubeCon NA 2025](../conferences/kubecon-na-2025.md).

Kubewarden's 2025 contribution is the **unified policy engine**: a single admission controller that runs Rego policies, CEL expressions, and Wasm modules side-by-side. Policy groups allow combining rules from different languages in one admission decision.

This matters for migration paths. Teams with existing OPA/Rego policies can adopt Kubewarden without rewriting, write new policies in CEL, and run both under one controller. The Wasm support additionally lets teams write policies in any language that compiles to WebAssembly (Rust, Go, AssemblyScript, Swift).

**Kyverno vs. Kubewarden:** Kyverno is the more popular choice (larger community, more documentation, stronger CI/CD integration). Kubewarden is the better choice if you have existing Rego policies you don't want to rewrite or if you want Wasm-portable rules that can run outside Kubernetes.

### Copacetic — patch images without rebuilding

**Repo:** `project-copacetic/copacetic` · License: Apache-2.0 · Go. Demoed at [KubeCon NA 2025](../conferences/kubecon-na-2025.md).

Copacetic addresses the chronic "wait for upstream to rebuild" remediation bottleneck. The workflow:

1. Run a vulnerability scanner (Trivy, Grype, etc.) against a container image.
2. Feed the scanner output to Copacetic.
3. Copacetic patches the vulnerable packages **in-place** — applies OS-level package updates directly to the image layers.
4. Push the patched image. No Dockerfile rebuild, no CI pipeline re-run.

This is not a replacement for proper image rebuilds — it's a **bridge** for the gap between "scanner found CVE-2025-XXXX" and "upstream published a fixed base image." The mean time from CVE disclosure to base-image rebuild is weeks to months; Copacetic closes it to minutes.

**Limitation:** Only works for OS-level packages (apt, yum, apk). Application-level vulnerabilities (npm, pip, Maven) still require rebuild.

### KIEMPossible — Kubernetes entitlement analysis

**Repo:** `PaloAltoNetworks/KIEMPossible` · License: Apache-2.0 · Python. Presented at [DEF CON 33](../conferences/defcon-33.md) Cloud Village.

KIEMPossible is the Kubernetes equivalent of cloud IAM entitlement analysis (like cloud-audit's IAM escalation graph, but for Kubernetes RBAC). It answers two questions:

1. **What permissions does each service account / user / group actually have?** (Role aggregation across RoleBindings, ClusterRoleBindings, and inherited permissions.)
2. **Which of those permissions are actually used?** (Audit-log correlation.)

The gap between "granted" and "used" is the attack surface. KIEMPossible visualizes it and identifies over-privileged service accounts — the Kubernetes analog of the AWS "unused IAM permissions" problem.

**Positioning:** KIEMPossible is the *analysis* layer; Kyverno/Kubewarden are the *enforcement* layer. KIEMPossible tells you "ServiceAccount X has cluster-admin but only uses pod/list." Kyverno's new DeletingPolicy or ValidatingPolicy can then enforce the tighter binding.

---

## Training / red-team manifests

Three tools that generate intentionally-insecure Kubernetes/container configurations for training and adversary emulation.

| | HoneyBee | BadPods | Caldera for OT |
|---|---|---|---|
| Author | Yaara Shriki (Wiz) | Bishop Fox (Seth Art) | MITRE |
| License | Apache-2.0 | MIT | Apache-2.0 |
| Function | Generate insecure Dockerfiles + Compose | Malicious K8s pod manifests for privesc | OT-protocol adversary emulation |
| Release surface | DEF CON 33 Cloud Village | Prior (still maintained) | DEF CON 33 Demo Labs |
| Use case | Dockerfile security training, scanner benchmarking | K8s privilege escalation training | ICS/SCADA attack simulation |

**HoneyBee** (`yaaras/honeybee`) auto-generates intentionally-insecure Dockerfiles and Docker Compose manifests modeling real-world misconfigurations (running as root, exposing secrets in ENV, writable filesystems, capability grants). Useful for: (a) training developers to spot Dockerfile anti-patterns, (b) benchmarking container scanners against known-bad inputs.

**BadPods** (`BishopFox/badPods`) is a collection of pod manifests that demonstrate Kubernetes privilege escalation paths — hostPath mounts, hostPID, hostNetwork, privileged containers, and combinations. The "BadPods" methodology was the basis for Seth Art's "Bad Pods: Kubernetes Pod Privilege Escalation" research. Use it to validate that your admission controller (Kyverno/Kubewarden/OPA) actually blocks each escalation path.

**Caldera for OT** (`mitre/caldera-ot`) extends MITRE Caldera with OT-protocol adversary emulation (Modbus, DNP3, BACnet, EtherNet/IP). Included here because containerized OT deployments on Kubernetes are increasingly common, and Caldera for OT is the tool that tests whether your detection stack (Falco/Tetragon/Tracee) catches OT-protocol abuse in containerized environments.

---

## How the layers compose

```
        Pre-deploy (CI)              Admission (runtime gate)           Runtime (detect + respond)
        ─────────────                ───────────────────────            ──────────────────────────
Scan    Spotter (CEL rules)          Kyverno (validate/mutate/image)    Falco (syscall detection)
        Trivy (CVE scan)             Kubewarden (Rego/CEL/Wasm)         Tetragon (eBPF enforcement)
                                                                        Tracee (Rego signatures)
Patch   Copacetic (image patch)      —                                  —

Audit   KIEMPossible (RBAC drift)   —                                  —

Test    HoneyBee / BadPods           —                                  Caldera for OT
        (generate bad manifests)                                        (adversary emulation)

Forensics   —                        —                                  StratoShark (syscall replay)
```

The three-stage pipeline:

1. **CI gate:** Spotter scans manifests for OWASP/CIS/NSA violations. Trivy scans images for CVEs. Copacetic patches what it can. KIEMPossible flags RBAC drift.
2. **Admission gate:** Kyverno or Kubewarden blocks resources that violate policy at deploy time.
3. **Runtime:** Falco/Tetragon/Tracee detect and (optionally) kill bad behavior. StratoShark captures forensic data when rules fire.

The **validation loop**: HoneyBee and BadPods generate known-bad inputs. Run them through all three stages. Anything that reaches runtime detection without being caught at CI or admission is a gap in your posture layer.

---

## CEL as the unifying thread

CEL (Common Expression Language) appears in every layer of this stack:

- **Spotter** — scanner rules written in CEL
- **Kyverno** — new ValidatingPolicy and MutatingPolicy use CEL
- **Kubewarden** — CEL as one of three supported policy languages
- **Kubernetes ValidatingAdmissionPolicy** — native K8s, CEL-only
- **Envoy** — CEL for authorization and rate-limiting
- **Tekton** — CEL for pipeline conditions

The implication: **CEL is the one policy-expression skill that transfers across the entire Kubernetes security stack**. Teams investing in Rego today should evaluate whether CEL covers their use cases — the ecosystem momentum has shifted. This pattern is also visible outside Kubernetes: [`Betterleaks`](./secret-scanning.md) uses CEL for secret-scanner filters, and [`Plumber`](./ci-cd-security.md) is evaluating CEL alongside its current Rego engine.

---

## Strategic recommendations

### For teams deploying Kubernetes in production

1. **Detection: start with Falco.** Largest rule community, CNCF graduated, lowest barrier to deployment. Add StratoShark when you need forensic-grade IR capability. Add Tetragon when you need inline enforcement or are already running Cilium.

2. **Admission: pick one of Kyverno or Kubewarden, not both.** Kyverno has the larger community and the more complete feature set after the 2025 policy types. Kubewarden is the right choice only if you have substantial existing Rego investment or need Wasm portability. Running both creates operational confusion.

3. **Scanning: Spotter + Trivy in CI.** Spotter covers configuration posture (OWASP/CIS/NSA). Trivy covers CVE/license/secret scanning. Copacetic bridges the remediation gap when you can't wait for upstream image rebuilds.

4. **RBAC hygiene: KIEMPossible quarterly.** Run KIEMPossible against audit logs, identify over-privileged service accounts, tighten bindings. Pair findings with Kyverno ValidatingPolicy to prevent regression.

5. **Validation: BadPods as the acceptance test for admission policies.** Deploy every BadPods manifest variant against your admission controller. Anything that gets through is a gap. Run HoneyBee-generated Dockerfiles through your CI image scanner — anything that passes is a scanner gap.

### For teams evaluating the landscape

- The **detection layer is stable**: Falco, Tetragon, and Tracee are all mature, actively maintained, and well-documented. Pick based on your CNI and policy-language preference.
- The **posture layer is still fragmenting**: Spotter, kube-bench, Polaris, kube-hunter, kubeaudit, and the native ValidatingAdmissionPolicy all overlap. Spotter's CEL alignment with the Kubernetes direction makes it the strongest new entrant.
- **Copacetic fills a real operational gap** that no other tool addresses. If your remediation SLA is measured in hours rather than weeks, it should be in your pipeline.
- **KIEMPossible is niche but important.** Kubernetes RBAC over-provisioning is universal and under-measured. This is the only OSS tool that correlates granted vs. used permissions.

### What's coming

1. **Falco + StratoShark integration will tighten.** Expect automated capture triggers, retention policies, and SIEM export in the StratoShark roadmap through 2026.
2. **Kyverno will absorb more of the admission stack.** The five new policy types already cover what previously required multiple tools. Image signing verification (ImageValidatingPolicy) positions Kyverno as the Sigstore/Cosign enforcement point.
3. **CEL will replace Rego for new Kubernetes policy work.** Rego remains powerful but CEL's inclusion in core Kubernetes APIs creates gravity that Rego cannot match. Kubewarden's multi-language support is the migration bridge.
4. **Container image patching will become a standard CI step.** Copacetic or a competitor will be as common as `trivy image scan` in CI pipelines by late 2026.
5. **The eBPF detection stack will get MCP wrappers.** Following the pattern from [Trivy MCP](../sources/appsec/trivy-mcp) and [cloud-audit MCP](./cloud-posture.md), expect Falco-as-MCP-tool and Tetragon-as-MCP-tool for agent-driven security operations.

---

## Cross-references

- [KubeCon NA 2025 notes](../conferences/kubecon-na-2025.md) — Kyverno, Kubewarden, Copacetic, Falco + StratoShark presentations.
- [DEF CON 33 notes](../conferences/defcon-33.md) — Spotter, KIEMPossible, HoneyBee, Caldera for OT releases.
- [defensive-ops.md](./defensive-ops.md) lines 68-83 — the eBPF defensive stack (Falco + StratoShark + Tetragon + Tracee + Little Snitch for Linux).
- [cloud-posture.md](./cloud-posture.md) — cloud-audit's IAM escalation graph is the AWS analog of KIEMPossible's Kubernetes RBAC analysis.
- [secret-scanning.md](./secret-scanning.md) — Betterleaks' CEL usage as another data point in CEL adoption.
- [ci-cd-security.md](./ci-cd-security.md) — SmokedMeat's OIDC pivot from CI to Kubernetes is the attack path this stack defends against.
- [`TOOLS.md`](../TOOLS.md) §4 — master index of all Kubernetes/container security tools.
