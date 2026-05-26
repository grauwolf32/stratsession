# eBPF runtime detection — Falco + StratoShark vs Tetragon vs Tracee

*Comprehensive comparison of the three eBPF-based Kubernetes/Linux runtime security tools active in 2025–2026.*

This report expands the detection-layer section of [`kubernetes-security.md`](./kubernetes-security.md) into a standalone deep-dive. All three tools instrument the Linux kernel via eBPF to detect (and optionally block) malicious behavior at runtime. The differences that matter in practice are: **where they hook the kernel**, **how they express policy**, **what they do when a rule fires**, **how noisy they are in production**, and **who maintains them**.

For the posture/admission layer (Spotter, Kyverno, Kubewarden, Copacetic, KIEMPossible), see [`kubernetes-security.md`](./kubernetes-security.md). For the host-firewall layer (Little Snitch for Linux), see [`defensive-ops.md`](./defensive-ops.md).

---

## At a glance

| | Falco + StratoShark | Tetragon | Tracee |
|---|---|---|---|
| **Maintainer** | Sysdig / CNCF | Isovalent (now Cisco) / Cilium | Aqua Security |
| **CNCF status** | **Graduated** (highest tier) | Incubating (under Cilium umbrella) | Not CNCF (vendor-hosted) |
| **License** | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| **Repo** | `falcosecurity/falco` + `sysdiglabs/stratoshark` | `cilium/tetragon` | `aquasecurity/tracee` |
| **Language** | C++ (kernel) + Go (userspace) | Go + C (eBPF programs) | Go + C (eBPF programs) |
| **Primary kernel hook** | Syscall boundary (kernel module or eBPF) | kprobes + tracepoints + **LSM hooks** | kprobes + tracepoints + **LSM hooks** |
| **Hook depth** | Syscall entry/exit only | Arbitrary kernel functions + LSM | Arbitrary kernel functions + LSM |
| **Rule/policy language** | YAML (Falco DSL with macros) | TracingPolicy CRD (YAML + selectors) | **Rego** (OPA) + YAML signatures |
| **Inline enforcement** | **No** (detect-only) | **Yes** (SIGKILL at LSM, pre-completion) | **Yes** (via LSM; also detect-only mode) |
| **Forensic capture** | **StratoShark** (Wireshark-style syscall replay) | No built-in | No built-in |
| **Network visibility** | Syscall-level (limited) | **Deep** (Cilium flow integration) | Moderate (eBPF network event tracing) |
| **K8s integration** | Pod/namespace metadata enrichment | **Native CRD** (TracingPolicy), namespace-scoped | Pod/namespace metadata enrichment |
| **Community rule library** | **100+ upstream rules** (largest) | Growing TracingPolicy library | 60+ built-in YAML signatures |
| **Companion tools** | StratoShark, Falcosidekick | Hubble (Cilium observability) | Trivy (same vendor, SCA) |
| **Best at** | Broadest detection + IR forensics | Kernel enforcement + network correlation | Rego-ecosystem alignment + detect-and-respond |

---

## 1. Kernel instrumentation — where they hook and why it matters

The single most important architectural difference is **where in the kernel each tool attaches its eBPF programs**.

```
                   User space
─────────────────────────────────────────────────
                   Syscall boundary          ← Falco hooks here
─────────────────────────────────────────────────
                   VFS / network / scheduler
─────────────────────────────────────────────────
                   kprobes / tracepoints     ← Tetragon + Tracee hook here
─────────────────────────────────────────────────
                   LSM hooks                 ← Tetragon + Tracee enforce here
─────────────────────────────────────────────────
                   Hardware
```

### Falco: syscall boundary

Falco intercepts at the **syscall entry/exit boundary** — the interface between userspace and kernel. This gives it visibility into every system call a process makes: `open`, `execve`, `connect`, `write`, `mmap`, etc. The original implementation used a kernel module; modern Falco uses an eBPF probe that attaches to the same syscall tracepoints.

**Strengths:** The syscall boundary is the most complete single observation point for process behavior. Every interaction with the OS passes through it. Falco's rule library is built on this: "process X opened file Y" and "process X connected to IP:port Z" are both syscall-level observations.

**Limitations:** Falco cannot see *inside* the kernel. A rootkit that modifies kernel data structures (task lists, file metadata) without issuing new syscalls is invisible at the syscall boundary. Falco also cannot enforce (block) — by the time the eBPF program runs at syscall entry, the only option is to log; there's no mechanism to prevent the syscall from completing. Enforcement requires an LSM hook, which Falco does not use.

### Tetragon: kprobes + tracepoints + LSM

Tetragon attaches eBPF programs at **three layers**: kprobes (arbitrary kernel function entry/exit), tracepoints (stable kernel instrumentation points), and LSM hooks (Linux Security Module callbacks). This gives it visibility into kernel internals that the syscall boundary doesn't expose: internal function calls, scheduler decisions, network-stack processing, and filesystem operations below the VFS layer.

**Strengths:** The LSM attachment is the key differentiator. LSM hooks are invoked **before** the kernel performs a security-sensitive operation (file access, process exec, network bind). Tetragon's eBPF program can return a **deny** verdict at the LSM hook, causing the kernel to abort the operation before it takes effect. This is **inline enforcement** — the process is killed (SIGKILL) or the operation is denied before damage completes. No userspace roundtrip, no race condition.

The kprobe attachment gives Tetragon the ability to monitor internal kernel functions that don't have syscall-level equivalents. Combined with Cilium's network flow data, a single TracingPolicy can express "alert when binary `/usr/bin/curl` in namespace `production` connects to an IP outside the expected CIDR range and then writes to `/etc/shadow`" — correlating network behavior with file-system behavior in one policy.

**Limitations:** kprobes are attached to specific kernel function symbols, which can change between kernel versions. Tetragon mitigates this with BTF (BPF Type Format) support, but very old kernels (pre-5.8) without BTF require manual configuration. The tight Cilium integration means non-Cilium clusters lose the network-flow correlation — Tetragon still works, but the policies that combine process + network context are Cilium-dependent.

### Tracee: kprobes + tracepoints + LSM (similar to Tetragon)

Tracee's kernel attachment is architecturally similar to Tetragon: kprobes, tracepoints, and LSM hooks. The difference is not *where* it hooks but *how it expresses policy on top of those hooks*.

**Strengths:** The same deep kernel visibility as Tetragon, plus LSM-based enforcement. Tracee's eBPF programs capture a broad set of kernel events and export them to userspace, where the **Rego signature engine** evaluates them against policy.

**Limitations:** The Rego evaluation happens in userspace, not in the eBPF program itself. This means Tracee's enforcement path has a userspace roundtrip that Tetragon's does not — though in practice the latency is sub-millisecond for most policies.

---

## 2. Policy authoring — three different models

### Falco rules: YAML DSL with macros

```yaml
- rule: Terminal shell in container
  desc: A shell was used as the entrypoint/exec in a container
  condition: >
    spawned_process and container
    and shell_procs
    and proc.tty != 0
    and container_entrypoint
  output: >
    Shell spawned in container
    (container=%container.name image=%container.image.repository
     shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline
     terminal=%proc.tty)
  priority: WARNING
  tags: [container, shell, mitre_execution]
```

**Characteristics:**
- Declarative, human-readable YAML
- **Macro system** for reusable conditions (`shell_procs`, `container_entrypoint` are macros expanding to lists of shell binary names and entrypoint detection logic)
- Conditions reference **Falco fields** (`proc.name`, `container.image.repository`, `fd.name`, `evt.type`) — a domain-specific vocabulary tied to Falco's syscall-level data model
- **100+ community-maintained rules** covering MITRE ATT&CK techniques for containers
- Output templating with field interpolation
- Mature, well-documented, extensive examples

**Learning curve:** Low for security analysts familiar with detection engineering. The field vocabulary (`proc.*`, `fd.*`, `evt.*`, `container.*`, `k8s.*`) takes a few hours to internalize. The macro system rewards investment — a well-maintained macro library makes new rules trivial.

### Tetragon TracingPolicy: Kubernetes CRDs

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-curl-to-external
spec:
  kprobes:
  - call: tcp_connect
    syscall: false
    args:
    - index: 0
      type: sock
    selectors:
    - matchBinaries:
      - operator: In
        values: ["/usr/bin/curl", "/usr/bin/wget"]
      matchNamespaces:
      - namespace: production
        operator: In
      matchActions:
      - action: Sigkill
```

**Characteristics:**
- Kubernetes-native CRD — deployed via `kubectl apply`, version-controlled with the rest of your cluster config
- **Selector-based matching:** binary path, namespace, labels, capabilities, argument values, kernel function arguments
- **Actions:** `Sigkill`, `Signal`, `Override` (change return value), `FollowFD`, `UnfollowFD`, `Post` (log only)
- Policies can target **any kernel function** (kprobe), not just syscalls — you can write policies that fire on `security_file_open`, `bprm_check_security`, or custom kernel module functions
- Namespace-scoped or cluster-wide deployment
- Inherits Cilium's identity model for pod selection

**Learning curve:** Moderate. Requires understanding of Linux kernel function names and argument types for kprobe-based policies. The selector model is intuitive for Kubernetes users, but the kernel-function targeting is a step up from Falco's application-level abstractions. Tetragon's documentation ships worked examples for common use cases (file integrity monitoring, process restriction, network policy enforcement).

### Tracee signatures: Rego + YAML

```rego
package tracee.TRC_2

import data.tracee.helpers

__rego_metadoc__ := {
    "id": "TRC-2",
    "version": "0.1.0",
    "name": "Anti-Debugging",
    "description": "Process uses anti-debugging technique",
    "tags": ["linux", "container"],
    "properties": {
        "Severity": 3,
        "MITRE ATT&CK": "Defense Evasion: Debugger Evasion",
    },
}

tracee_selected_events[eventSelector] {
    eventSelector := {
        "source": "tracee",
        "name": "ptrace",
    }
}

tracee_match {
    input.eventName == "ptrace"
    arg := helpers.get_tracee_argument("request")
    arg.value == "PTRACE_TRACEME"
}
```

**Characteristics:**
- **Rego** (the OPA policy language) for complex detection logic — if/then/else, iteration, aggregation, external data
- **YAML signatures** (60+) for simpler pattern matches — same idea as Falco rules but with Tracee's event vocabulary
- Rego enables **stateful detection**: correlate multiple events over time, maintain context across syscalls, aggregate patterns (e.g., "more than 10 failed `open` calls on `/etc/shadow` within 5 seconds")
- Can import external data sources (threat feeds, allowlists) into Rego policy evaluation
- The same policy language used by OPA/Gatekeeper admission control — skills transfer directly

**Learning curve:** High for teams without Rego experience. Rego is a full logic-programming language, not a configuration format. However, for teams already running OPA/Gatekeeper for admission control, the investment is already made — and having detection rules and admission policies in the same language is a genuine operational advantage.

---

## 3. Enforcement — the critical differentiator

| | Falco | Tetragon | Tracee |
|---|---|---|---|
| Can block/kill? | **No** | **Yes** | **Yes** |
| Enforcement mechanism | N/A | SIGKILL via LSM hook (in-kernel) | SIGKILL via LSM hook (kernel→userspace→kernel) |
| Enforcement latency | N/A | **Sub-microsecond** (no userspace roundtrip) | Sub-millisecond (userspace Rego eval) |
| Enforcement granularity | N/A | Per-syscall / per-kernel-function | Per-event (after Rego evaluation) |
| False-positive risk | N/A (detect-only) | **High** (killing a legit process is disruptive) | Moderate (Rego logic can be more nuanced) |
| Operational pattern | Alert → SIEM → human triage | Kill → log → investigate | Alert or kill based on Rego verdict |

### Why Falco chose detect-only

Falco's design philosophy is that **detection and enforcement should be separate concerns**. The argument: a detection system that can kill processes becomes a reliability risk — a false-positive rule kills a production workload. By keeping Falco detect-only, the blast radius of a bad rule is a noisy alert, not a production outage. Enforcement is delegated to purpose-built tools: Kubernetes admission controllers (Kyverno, Kubewarden), network policies (Cilium, Calico), or response engines (Falcosidekick → webhook → remediation).

**Falcosidekick** (`falcosecurity/falcosidekick`) is the standard response router: it takes Falco alerts and forwards them to 60+ outputs (Slack, PagerDuty, SIEM, webhook, Kubernetes Event, AWS Lambda, etc.). The critical response path is: Falco → Falcosidekick → webhook → custom remediation logic (e.g., cordon the node, kill the pod, trigger a forensic capture).

### Why Tetragon chose inline enforcement

Tetragon's design philosophy is that **some threats must be stopped before they complete**. The argument: if an attacker executes `rm -rf /` inside a container, a detect-only system logs the event after the files are gone. Tetragon's LSM-hook enforcement kills the process before the `unlink` syscalls complete. The trade-off is explicit: you accept the operational risk of false-positive kills in exchange for the security guarantee that detected threats are stopped in-kernel.

**In practice:** most Tetragon deployments start in **observe mode** (log only), tune policies over weeks, then selectively enable enforcement for high-confidence policies (e.g., "no process except `nginx` should bind to port 80 in the `web` namespace"). The recommendation is: enforce on behavior that is **never legitimate** (binary execution in a scratch container, writes to `/etc/passwd` in a distroless image), alert on everything else.

### Tracee's hybrid approach

Tracee supports both modes. The default is detect-only (like Falco); enforcement is opt-in per signature. The Rego evaluation adds a layer of logic between the kernel event and the enforcement decision — you can write a Rego rule that says "kill this process only if it matches pattern A *and* doesn't match exception B *and* the container is in namespace C." This nuance reduces false-positive kills compared to Tetragon's selector-based approach, at the cost of enforcement latency (userspace Rego evaluation adds sub-millisecond delay).

---

## 4. Network visibility

| | Falco | Tetragon | Tracee |
|---|---|---|---|
| Mechanism | Syscall-level `connect`/`accept`/`sendto` | **Cilium flow data** + eBPF network hooks | eBPF network event tracing |
| Visibility | Source/dest IP:port per syscall | **Full L3/L4/L7 flow metadata** (HTTP headers, DNS queries, gRPC methods) | Source/dest IP:port + protocol detection |
| Cross-correlation | Process → network syscall (manual) | **Process → network flow** (automatic, single policy) | Process → network event (manual correlation) |
| DNS visibility | Only via `connect` to port 53 | **DNS query/response content** (via Cilium DNS proxy) | DNS event tracing (query names visible) |
| Cilium required? | No | **For full capability, yes** | No |

Tetragon's network visibility is categorically deeper than the other two when running with Cilium. A TracingPolicy can express "alert when any process in the `payments` namespace makes an HTTP request to a domain not in the allowlist" — this requires L7 (HTTP) flow data that only Cilium's datapath provides. Falco and Tracee see the `connect` syscall to the destination IP, but not the HTTP Host header or URL path.

Without Cilium, Tetragon's network visibility drops to the same level as Tracee (eBPF network hooks, L3/L4 only). This is the primary operational constraint: **Tetragon's network superpower is Cilium-dependent**.

---

## 5. Production deployment — operational realities

### Falco: expect 3 weeks of tuning

The most operationally honest public account: ["Falco in Production: Tuning, Integration, and Operational Realities"](https://liveaverage.com/blog/kubernetes/2026-03-23-how-are-you-actually-using-falco-in-production/) (March 2026).

Key findings:
- **>5,000 alerts/day initially** with default rules on a modest production cluster
- **Top noise sources:** Spring Boot health checks triggering `k8s_api_server_connection`, init containers spawning shells, sidecar proxies (Envoy/Istio) triggering network rules, CronJobs triggering `suspicious_process_in_container`
- **Tuning workflow:** disable noisy rules → add exceptions for known-good patterns → re-enable with narrowed conditions → repeat weekly for 3 weeks
- **Time-to-value:** 3 weeks before PagerDuty integration becomes viable (alert volume drops to ~50-100/day after tuning)
- **eBPF mode on managed K8s:** EKS/GKE/AKS restrict kernel-module loading; use the eBPF probe (`falco-driver-loader --type ebpf`). Performance is equivalent; the kernel module is legacy.

**Deployment pattern:** DaemonSet (one Falco pod per node) + Falcosidekick for alert routing + StratoShark for on-demand forensic captures.

### Tetragon: Cilium-native, lower noise

Tetragon benefits from starting in observe mode with a narrow initial policy set rather than a broad default rule library. The typical deployment:

1. Deploy Tetragon DaemonSet alongside Cilium
2. Start with built-in process-exec and file-access observers (no enforcement)
3. Analyze observed behavior for 1-2 weeks (via Hubble UI or Grafana dashboards)
4. Write TracingPolicies targeting specific violations (binary execution in restricted namespaces, writes to sensitive paths)
5. Enable enforcement selectively on high-confidence policies

**Alert volume:** inherently lower than Falco because Tetragon doesn't ship a 100+ rule default set — you build up from zero. This is both a strength (less noise) and a weakness (less out-of-box coverage).

**Performance overhead:** lower than Falco for enforcement decisions because the eBPF program makes the kill/allow decision in-kernel with no userspace roundtrip. The trade-off: complex selector matching in eBPF programs consumes per-syscall CPU cycles. Benchmark on your workload before enforcing on hot paths.

### Tracee: Aqua ecosystem integration

Tracee deploys as a DaemonSet. The operational advantage is **vendor alignment with Trivy**: organizations already running Trivy for SCA/container scanning get a single-vendor stack (Aqua) covering both build-time scanning and runtime detection. The 60+ built-in signatures provide faster time-to-value than Tetragon's build-from-zero approach, though less coverage than Falco's 100+ rules.

**Rego rule maintenance:** the operational cost of Rego is real. Rego rules are more powerful than Falco YAML or Tetragon CRDs, but they're also harder to review, test, and debug. Organizations with an existing OPA/Gatekeeper deployment absorb this cost naturally; organizations without Rego experience should factor in the learning curve.

---

## 6. StratoShark — the forensic differentiator

**Repo:** `sysdiglabs/stratoshark` — Created by Gerald Combs (Wireshark founder). Presented at [KubeCon NA 2025](../conferences/kubecon-na-2025.md).

StratoShark is a **Wireshark-style forensic interface for syscall captures**. It uses the same filter/dissector model that Wireshark uses for network packets, applied to the Falco syscall capture format. This is not a SIEM visualization — it's a packet-analysis-grade forensic tool for syscall-level investigation.

### Workflow

```
Falco rule fires
    ↓
Targeted syscall capture begins on the container/pod
    ↓
Capture file (.scap) saved to persistent storage
    ↓
Analyst opens .scap in StratoShark
    ↓
Full syscall-level replay: file ops, network calls, process trees,
    memory maps, file descriptors — with Wireshark-style filters
```

### What StratoShark shows that SIEM alerts don't

A Falco alert says: "shell spawned in container `web-frontend-abc123` at 14:32:07 UTC." A StratoShark capture of the same event shows:

- Every file the shell process opened, read, and wrote
- Every network connection it made (with payload bytes)
- Every child process it spawned (with full command lines)
- Every environment variable in the process
- The complete process tree from PID 1 to the shell
- File descriptor inheritance across `fork`/`exec`

This is the difference between an alert and an investigation. Neither Tetragon nor Tracee have an equivalent — their forensic path is "export events to a SIEM and build dashboards."

### Why it doesn't replace Tetragon/Tracee

StratoShark is post-incident. It tells you what happened after the fact. It does not prevent anything. The complementary model: Tetragon enforces (prevents), Falco detects (alerts), StratoShark investigates (forensics). Running all three is not overkill — they cover three different time horizons of the same incident.

---

## 7. Decision matrix

### Pick Falco + StratoShark when:

- Detection breadth is the priority (100+ rules, largest community)
- Post-incident forensics is a requirement (StratoShark has no equivalent)
- Enforcement is handled by other tools (admission controllers, network policies)
- You want the lowest-risk deployment (detect-only means no false-positive kills)
- Team has detection-engineering skills but not kernel-internals expertise
- CNCF Graduated status matters for procurement/compliance

### Pick Tetragon when:

- Inline enforcement is required (kill before damage completes)
- You're already running Cilium as your CNI
- Network-flow-correlated detection is needed (L7 visibility requires Cilium)
- You want Kubernetes-native policy management (CRDs, namespace-scoped)
- Team has kernel/eBPF expertise or is willing to invest
- You're building a zero-trust workload identity model (Cilium identity + Tetragon enforcement)

### Pick Tracee when:

- Rego expertise already exists (OPA/Gatekeeper users)
- Single-vendor alignment with Trivy matters (Aqua stack)
- You need stateful detection logic (Rego can correlate events over time)
- Both detection and selective enforcement are needed
- The team prefers policy-as-code in a general-purpose language over DSLs

### Run multiple when:

The three tools are **more complementary than competitive**. Production-grade deployments that need detection + enforcement + forensics will run at least two:

| Combination | Use case |
|---|---|
| **Falco + Tetragon** | Detection breadth (Falco) + enforcement (Tetragon) + forensics (StratoShark). The recommended pairing for Cilium shops. |
| **Falco + Tracee** | Detection breadth (Falco) + Rego-based custom detection (Tracee) + forensics (StratoShark). For OPA-ecosystem shops. |
| **Tetragon + Tracee** | Enforcement (Tetragon) + Rego detection (Tracee). Unusual — overlapping kernel hooks. |
| **All three** | Maximum coverage. Only justified for high-security environments where the operational cost of three DaemonSets is acceptable. |

---

## 8. The eBPF defensive stack in 2026

These three tools are part of a broader eBPF-native defensive layer that became complete in 2025-2026:

```
                 Container workloads              Bare-metal / VM hosts
                 ───────────────────              ─────────────────────
  Detection      Falco (broad)                    Falco (broad)
                 Tetragon (deep + enforcement)    Tetragon (deep + enforcement)
                 Tracee (Rego-based)              Tracee (Rego-based)

  Forensics      StratoShark (syscall replay)     StratoShark + mquire (memory)

  Network        Cilium (L3-L7 policy)            Little Snitch for Linux (per-process)

  Enforcement    Tetragon (process kill)           Tetragon (process kill)
                 Cilium NetworkPolicy (network)    Little Snitch (network)
```

The strategic takeaway from [`defensive-ops.md`](./defensive-ops.md): 2025–2026 is when the eBPF defensive layer became **complete enough** to recommend an eBPF-first defensive stack as the primary security layer — not a supplement to traditional host-based tools.

---

## Cross-references

- [kubernetes-security.md](./kubernetes-security.md) — parent report covering the full K8s security stack (detection + posture + admission)
- [defensive-ops.md](./defensive-ops.md) lines 68-83 — eBPF stack architecture and Little Snitch for Linux
- [KubeCon NA 2025 notes](../conferences/kubecon-na-2025.md) — StratoShark announcement
- [TOOLS.md](../TOOLS.md) §4 — Falco, Stratoshark, KIEMPossible tool entries
- [blogs/oss-usage-case-studies.md](../blogs/oss-usage-case-studies.md) lines 16-21 — Falco production deployment case studies
- [teampcp-postmortem.md](./teampcp-postmortem.md) — self-hosted runner monitoring with Falco/Tetragon for CI/CD defense
- [firmware-memory-forensics.md](./firmware-memory-forensics.md) — mquire for Linux memory forensics (companion to StratoShark for host-level IR)
