# CI/CD pipeline security — SmokedMeat · Plumber · Brutus

Three tools released between Jan–Apr 2026 that together cover the **attack → posture → credential validation** triangle for modern CI/CD: SmokedMeat (offensive), Plumber (defensive), and Brutus (credential validation on the back of a pipeline compromise).

The category exists because the **TeamPCP incident (March 2026)** finally made build-pipeline compromise a tier-1 risk: a single actor chained injection in GitHub Actions workflows to ship malicious updates through Trivy, LiteLLM, KICS, Telnyx, and several dozen npm packages. SmokedMeat is the post-incident red-team kit; Plumber is the post-incident GitLab compliance scanner; Brutus is the credential validator that you reach for once secrets fall out of a compromised runner.

| | SmokedMeat | Plumber | Brutus |
|---|---|---|---|
| Side | Offensive (red team) | Defensive (compliance) | Offensive (credential testing) |
| Target | GitHub Actions orgs | GitLab CI + GitHub Actions | Any network service |
| Author | Boost Security Labs (François Proulx) | r2devops / getplumber | Praetorian Labs |
| License | AGPL-3.0 | MPL-2.0 | Apache-2.0 (Praetorian standard) |
| Language | Go (TUI + C2 + implant) | Go | Go |
| Form factor | 3-component framework (Counter / Kitchen / Brisket) | Single CLI + GitLab CI component | Single CLI + Go library |
| Release | April 15, 2026 | v0.2.x stable Jan 19, 2026; v0.3.0 beta May 2026 | February 13, 2026 |
| Submodule | [`sources/ci-cd/smokedmeat`](../sources/ci-cd/smokedmeat) | [`sources/ci-cd/plumber`](../sources/ci-cd/plumber) | [`sources/perimeter/brutus`](../sources/perimeter/brutus) |

These are the operational counterpart to the AIxCC OSS CRSs already documented in [`ai-vuln-research.md`](./ai-vuln-research.md): one is "find the bug end-to-end in source"; this trio is "compromise the pipeline that ships the code."

---

## SmokedMeat — the CI/CD Metasploit

**Repo:** `boostsecurityio/smokedmeat` · License: **AGPL-3.0** · Go 1.26+. Maintained by Boost Security Labs (same team behind the [poutine](https://github.com/boostsecurityio/poutine) build-pipeline SAST scanner).

SmokedMeat is the first OSS red-team framework purpose-built for **build pipelines** (not "general C2 that happens to work on a runner"). The framing the project uses — "Like Metasploit, but for CI/CD" — is accurate; the architecture is a direct C2 framework analog:

| Standard term | SmokedMeat name | Role |
|---|---|---|
| Operator TUI | **Counter** | Bubbletea v2 terminal interface |
| C2 teamserver | **Kitchen** | HTTP + WebSocket API, NATS JetStream bus, BBolt graph DB |
| Implant | **Brisket** | Agent dropped on the CI runner via stager |
| Browser graph view | **Browser View** | Live Cytoscape.js attack graph at `/graph` |

### Why it's a category-defining release

1. **Full kill-chain in one tool, scoped to pipelines.** Traditional C2 (Sliver, Mythic, Empire) treats a CI runner as just another endpoint. SmokedMeat treats it as **the** endpoint and bakes in every primitive a CI/CD red-teamer needs:
   - Recon via embedded [**poutine**](https://github.com/boostsecurityio/poutine) SAST — finds injection vulns, dangerous triggers, unsafe checkout in GitHub Actions workflows.
   - Delivery via **5 automated methods**: PR, issue, comment, **LOTP** (Living Off The Pipeline), or `workflow_dispatch`.
   - Memory-scanning Runner.Worker process via `/proc` (component named **gump**) to recover the unmasked values of `secrets.*`, `vars.*`, and the per-job `GITHUB_TOKEN` permission map that GitHub deliberately hides from the action's own log.
   - OIDC token exchange for AWS (`sts:AssumeRoleWithWebIdentity`), GCP Workload Identity Federation, Azure AAD, and Kubernetes — i.e., the canonical cloud-pivot from a compromised pipeline.
   - SSH deploy-key probing and GitHub App PEM → installation-token exchange.

2. **Whooli — a Goat for CI/CD.** SmokedMeat ships with a **deliberately-vulnerable GitHub organization** (`github.com/whooli`) as its training environment. This is the OWASP Juice Shop / DVWA equivalent for build pipelines — every quickstart points new operators at `whooli` first. No other CI/CD red-team toolchain has shipped a target environment of comparable depth.

3. **LOTP catalog — 15 build tools with config-file payloads.** "Living Off The Pipeline" is the discipline of getting code execution inside `install` / `build` / `test` steps by abusing legitimate build-tool config files (npm `preinstall`, pip `setup.py`, cargo `build.rs`, Makefile recipes, etc.). SmokedMeat ships a curated catalog of payloads for **npm, pip, cargo, make, docker, gradle, maven, and more**. The category as documented at [boostsecurityio.github.io/lotp](https://boostsecurityio.github.io/lotp/) is one of the most operationally important attack classes in CI/CD; SmokedMeat is the first OSS framework that **operationalizes** the whole catalog.

4. **Context-aware injection payload generator.** Eight injection vectors are modeled — branch name, PR title, PR body, commit message, issue title, issue body, `github-script`, bash `run` — with constraint-aware techniques (e.g., character set, length cap, quote handling). This is the same idea as Burp's payload library, scoped to GHA workflow injection.

5. **Persistent attack graph.** BBolt-backed directed graph (org → repo → workflow → job → vuln → token → cloud-resource) with nodes added during recon and exploitation, and a live Cytoscape.js viewer. The graph is the operational view of "blast radius" — after each pivot the operator sees what just unlocked.

6. **Cache poisoning workflow.** A wizard-driven flow that classifies a repo's GHA Actions Cache writer/victim pattern, predicts exact cache keys, stages a poisoned archive via the Cache API, and arms the implant for re-execution on the next consumer hit. This is one of the most consequential GHA attack primitives published in 2025–2026 and not a feature of any general-purpose C2.

7. **Cloud Shell — a durable per-engagement workspace.** A pre-configured container with `gcloud` / `aws` / `az` installed and credentials threaded through; "cloud export" persists captured cloud creds back to the operator's local stash. This is what Mythic / Havoc operators have to build by hand.

### Where it sits vs. prior work

The README's own "Prior Art" list is honest about lineage:

| Influence | Contribution to SmokedMeat |
|---|---|
| **poutine** (same team) | Embedded as the recon SAST engine. |
| **Gato-X** (Adnan Khan) | The GitHub Actions enumeration / abuse vocabulary. |
| **Nord-Stream** (Synacktiv) | The original "extract CI secrets from runner memory" research. |
| **Sliver** (Bishop Fox) | Go-based C2 architecture patterns. |
| **Mythic** | Operator-collaboration model (multi-operator teamserver, WebSocket events). |

What's net-new vs. all five: the **full attack lifecycle wrapped in one cohesive TUI**, the **LOTP-catalog-as-payload-library**, the **cache-poisoning wizard**, and the **whooli range**.

### Strategic positioning

SmokedMeat is **explicitly bold and noisy** — the README says so: *"This isn't an EDR evasion tool. It's a demonstration framework that shows how deep a CI/CD compromise goes before anything triggers an alert."* This is the right framing for a defensive validation tool. If you want stealth, use Sliver/Havoc on the runner. If you want a curriculum and a kill-chain map for "what TeamPCP could do to us," this is the tool.

For a Russian-speaking AppSec team in 2026 the implication is concrete: **set up Whooli + SmokedMeat in a sandbox, run a tabletop with your platform engineers, then measure how many of the techniques your existing GitHub Advanced Security / Datadog / Falco setup actually catches**. The answer will not be flattering — that's the point.

---

## Plumber — the GitLab-first (now GitHub-second) compliance scanner

**Repo:** `getplumber/plumber` · License: **MPL-2.0** · Go. Maintained by r2devops, OpenSSF Scorecard + SLSA L3 attested.

Plumber is what the *defender* runs after watching a SmokedMeat demo. It's a CI/CD compliance CLI that reads `.gitlab-ci.yml` (and resolved includes) via the GitLab API, then evaluates a single Rego policy engine against the **pipeline + repository settings** combined.

v0.3.0-beta (May 2026) adds **GitHub Actions** support alongside GitLab — `.github/workflows/*.{yml,yaml}` from a local clone (offline-first) or via GitHub API.

### What's novel

1. **One CLI, one Rego engine, two providers.** The control set is split per-provider in `.plumber.yaml` (`gitlab.controls:` / `github.controls:`), but the underlying engine is the same Rego policy evaluator. Compare to most "CI/CD scanners" which are provider-specific (Tinfoil, Legitify, Gato-X, poutine — all GitHub-only at release).

2. **Pipeline + repo settings together, not just YAML lint.** Plumber doesn't just parse the workflow file; it queries the provider's API for **branch protection, force-push rules, code-owner-approval, GITHUB_TOKEN permissions, etc.** The Rego rules operate over a normalized IR that includes both layers. A workflow that looks fine in isolation can still fail "default branch has no force-push protection" — Plumber catches that.

3. **Provider-agnostic IR.** The "provider-agnostic IR" is the part that lets a single Rego policy reason over a GitLab include graph and a GitHub workflow tree. Adding a third provider (Bitbucket Pipelines is on the roadmap) would mean writing a third normalizer, not a third policy set.

4. **Coverage matches the most common attack classes.**

   GitLab CI (14 controls):
   - Mutable image tags / untrusted registries
   - Unprotected branches, missing force-push & code-owner-approval
   - Hardcoded jobs not from reusable components
   - Outdated / forbidden include refs (`main`, `HEAD`)
   - `CI_DEBUG_TRACE` exposure (secret leakage in job logs)
   - Unsafe variable injection via `eval` / `sh -c` (**OWASP CICD-SEC-1**)
   - Weakened security jobs — `allow_failure: true`, `when: manual`, `rules: [{when: never}]` on SAST/Secret-Detection (**OWASP CICD-SEC-4**)
   - Docker-in-Docker on shared runners (container escape)

   GitHub Actions (9 controls):
   - Third-party actions referenced by tag/branch instead of SHA (**CVE-2025-30066** class)
   - Missing `permissions:` block (defaults to repo-wide `GITHUB_TOKEN`)
   - Dangerous triggers (`pull_request_target`, `workflow_run`) running with base-repo secrets
   - Reusable workflow `secrets: inherit` (vs. explicit map)
   - Template-injection sinks `${{ github.event.* }}` interpolated into `run:`
   - Weakened scanners with `continue-on-error: true`
   - DinD on GitHub-hosted runners

5. **Outputs include PBOM and CycloneDX SBOM.** Plumber emits a **Pipeline Bill of Materials** (PBOM) — every pinned action, every image SHA, every included template ref — and a CycloneDX SBOM at the same time. This is the pairing that Sunshine + Trivy already gives you for code dependencies; Plumber gives it for pipeline dependencies.

6. **Soft-degrade design.** GitHub local-clone mode runs the workflow-content controls without a token at all (repo-level controls silently abstain). This is friendly for "I want to scan a fork I can't auth against" and for offline CI runs. Most CI/CD scanners refuse to run without API access.

7. **Two deployment modes.** Run the CLI, or drop in **2 lines** as a GitLab CI Component that auto-evaluates against the default branch, tags, and open MRs on every pipeline.

### Operational positioning

Plumber is the **defensive companion** to SmokedMeat, even though they target different providers as their first-class case (SmokedMeat = GitHub, Plumber = GitLab — with v0.3.0 narrowing the gap). For a team where the threat model spans both providers (most enterprises) you want **both** running.

The tool worth checking it against directly is GitHub's [own action `pinact`](https://github.com/suzuki-shunsuke/pinact) (action pinning), [`zizmor`](https://github.com/woodruffw/zizmor) (Woodruff's GHA SAST), and [`poutine`](https://github.com/boostsecurityio/poutine) (SmokedMeat's own SAST engine). None of those cover **repository-settings-as-policy** and none of them are GitLab-first. Plumber's wedge is exactly that.

---

## Brutus — the modern multi-protocol credential validator

**Repo:** `praetorian-inc/brutus` · License: Praetorian-standard Apache-2.0 · Go (zero CGO). Released February 13, 2026.

Brutus is the closest thing to a 2026 replacement for THC Hydra. It is **not** strictly a CI/CD tool, but it earns a spot in this report because the canonical post-SmokedMeat workflow is: *pipeline → secret extraction → "where do these SSH keys / DB creds work?"* — which is exactly Brutus's wheelhouse.

### What's novel vs. Hydra / Medusa / Ncrack

| Feature | Hydra | Medusa | Ncrack | **Brutus** |
|---|:-:|:-:|:-:|:-:|
| Single binary, zero deps | ❌ | ❌ | ❌ | ✅ |
| Native pipeline integration (JSON in/out) | ⚠️ | ❌ | ❌ | ✅ |
| Cross-platform (Linux/macOS/Windows) | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Embedded SSH bad-key collection | ❌ | ❌ | ❌ | ✅ |
| Go library import (`pkg/brutus`) | ❌ | ❌ | ❌ | ✅ |
| Active development | ✅ | ⚠️ | ❌ | ✅ |

**24 protocols** supported at release. The breadth is wider than any single competitor: SSH, FTP, Telnet, VNC, RDP, SNMP, HTTP(S) Basic, SMB, LDAP, WinRM, MySQL, PostgreSQL, MSSQL, MongoDB, Redis, Neo4j, Cassandra, CouchDB, Elasticsearch, InfluxDB, SMTP, IMAP, POP3.

### Standout primitives

1. **Embedded SSH bad keys.** [rapid7/ssh-badkeys](https://github.com/rapid7/ssh-badkeys) + HashiCorp Vagrant insecure key + appliance-vendor static keys (F5 BIG-IP `CVE-2012-1493`, ExaGrid `CVE-2016-1561`, Barracuda `CVE-2014-8428`, Ceragon `CVE-2015-0936`, Array Networks, Quantum DXi, Loadbalancer.org) — **compiled into the binary**. `--badkeys-only` is a one-liner audit across `/24` ranges. Every key is paired with the right default username (Vagrant→vagrant, F5→root, etc.) and CVE-tracked for compliance queries. This is unique to Brutus.

2. **RDP sticky-keys backdoor detection & exploitation.** Brutus implements MITRE ATT&CK **T1546.008** detection end-to-end:
   - Connect to RDP target (non-NLA)
   - Capture login-screen baseline bitmap
   - Send 5× Shift (the sticky-keys trigger)
   - Capture response bitmap
   - Heuristic pixel-diff to detect a terminal window
   - Optional Claude Vision confirmation (`--experimental-ai`)
   - `--sticky-keys-exec "<cmd>"` — type a command into the pre-auth `cmd.exe` and save a PNG of the result
   - `--sticky-keys-web` — live browser-based RDP viewer (JPEG over WebSocket, ~10 FPS, full keyboard + mouse) for interactive control of the pre-auth backdoor

   Even more useful is the two-phase scan-only mode (`--nla-check` then `--sticky-keys-scan`) that emits JSONL classified findings for pipeline integration. This is the only OSS tool that automates the entire sticky-keys MITRE-mapped chain.

3. **RDP support via IronRDP-in-WASM.** To keep zero-CGO single-binary build, Brutus compiles Devolutions' [IronRDP](https://github.com/Devolutions/IronRDP) (Rust) to WebAssembly and runs it via [wazero](https://github.com/tetragoral/wazero). This is a delightful piece of engineering — Rust protocol parsers shipped as WASM modules inside a Go binary — and the pattern is reusable. Expect similar techniques for other complex protocols (Citrix ICA, mainframe TN3270, etc.).

4. **Pipeline-native JSON I/O.** The canonical workflow is `naabu → nerva → brutus` (Praetorian's own [nerva](https://github.com/praetorian-inc/nerva) service-fingerprinter sits in the middle):
   ```bash
   naabu -host 10.0.0.0/24 -p 22,3306,5432,6379,27017,445 -silent | \
     nerva --json | \
     brutus --json -o results.json
   ```
   Brutus parses the nerva JSON stream, maps services to protocols, tests default credentials, outputs successful credentials only. No format glue.

5. **Go library, not just CLI.** `import "github.com/praetorian-inc/brutus/pkg/brutus"` — call `brutus.Brute(config)` from your own Go automation. Hydra has no equivalent.

6. **Experimental AI for HTTP admin panels.** `--experimental-ai` (requires `ANTHROPIC_API_KEY`) uses **Claude Vision** to look at the rendered login page screenshot, identify the device/application, and propose default credentials drawn from training data. Optional **Perplexity** integration adds live web search. Tackles the "what is this random admin panel and what are its default creds" problem that has resisted automation forever. Form-based auth uses headless Chromium to actually submit the credentials.

### Where Brutus fits in the stratsession picture

Brutus is the natural **right-hand of [`Vespasian`](../sources/appsec/vespasian) + [`Hadrian`](../sources/appsec/hadrian)** for the network layer — the same way Vespasian/Hadrian own API attack surface, Brutus owns service-credential attack surface. All three are from Praetorian's post-engagement OSS pipeline (the same pipeline that ships [`OAuthSeeker`](https://github.com/praetorian-inc/oauthseeker), [`Julius`](https://github.com/praetorian-inc/julius), and [`nerva`](https://github.com/praetorian-inc/nerva)). The story Praetorian is telling, repo by repo, is "consultancy-grade offensive primitives, OSS-released after we've used them in engagements."

For a CI/CD-focused workflow specifically: after SmokedMeat extracts secrets from a runner, Brutus is the fastest way to find **where those secrets work** across the rest of the network — internal databases, jump hosts, admin panels behind reverse proxies, infra appliances with static SSH keys. The combination is brutal.

---

## How the three compose for a 2026 CI/CD assessment

```
Recon                              Offensive validation              Defense
─────────────────                  ─────────────────────             ──────────
poutine (embedded)         ──►    SmokedMeat full chain     ◄──►   Plumber (compliance gates)
zizmor / Gato-X (alt)             ├── Whooli range                  ├── GitLab CI Component
                                  ├── LOTP payloads                  ├── PBOM + CycloneDX
                                  ├── Cache poisoning                └── Merge-request comments
                                  ├── Memory secret scrape
                                  ├── OIDC cloud pivot
                                  └── Captured creds
                                          ↓
                                     Brutus (validate creds at scale)
                                          ↓
                                     Findings → DefectDojo
```

The defenders' angle: run **Plumber on every pipeline** (compliance-gate), **SmokedMeat against Whooli quarterly** (tabletop exercises), and treat **Brutus output** as the answer to "if a pipeline secret leaks, what's the blast radius."

The attackers' angle: SmokedMeat to compromise the pipeline, then Brutus on the captured credentials, then [`OAuthSeeker`](https://github.com/praetorian-inc/oauthseeker) for any captured OAuth state that survived.

---

## Where the category is going

1. **TeamPCP wasn't a one-off.** The incident is the inflection point — every major CI/CD vendor's roadmap shifted by Q2 2026. Expect at least two more comparable incidents in 2026, and expect SmokedMeat-style frameworks to add **GitLab CI** as a first-class target (today it's GitHub-only) within 6 months.

2. **OSS compliance scanners will fill the CI/CD CSPM gap.** Plumber is the leading OSS GitLab-and-GitHub compliance scanner; expect commercial CSPM vendors (Wiz, Orca, Lacework) to either ship equivalents or **OEM Plumber**. The OpenSSF Scorecard + SLSA L3 attestation Plumber ships with is the same "trust-on-first-install" posture commercial CSPMs need.

3. **The credential-spraying primitive is consolidating in Go.** Brutus is one of several Go-native bruteforce/credential tools that emerged in 2025–2026 (others: [`pwndoc`](https://github.com/pwndoc) Go-based variants, [`nemesis`](https://github.com/SpecterOps/Nemesis)). The Hydra → Go migration is happening, and Brutus is the most polished implementation. Expect Praetorian to keep extending the protocol matrix (Kerberos, MQTT, AMQP, MSRPC are obvious gaps).

4. **CI/CD attack surface will get a Goat archetype.** Whooli is the first "deliberately-vulnerable GitHub org." Expect 2–3 competitors (CyberCNS or Snyk could ship one; Bishop Fox already has [`cloudfoxable`](https://github.com/BishopFox/cloudfoxable) for cloud) — that's the cue for AppSec training programs to add a CI/CD module on top of the existing crAPI / Juice Shop / DVWA curriculum.

5. **MCP wrapping is coming.** Cloud-audit (a sibling tool reviewed in [`cloud-posture.md`](./cloud-posture.md)) already ships an MCP server. None of SmokedMeat / Plumber / Brutus ship MCP servers at release, but the wrapper pattern from [Trivy MCP](../sources/appsec/trivy-mcp) is now a one-week effort — expect Brutus-as-MCP-tool and Plumber-as-MCP-tool inside Q3 2026. SmokedMeat itself probably stays human-driven.

The strategic point: CI/CD security in 2025 was a buzzword and a few SAST checks; in 2026 it is a **full kill-chain discipline** with offensive tooling, defensive tooling, training ranges, and a flagship incident that justifies the budget for all three.
