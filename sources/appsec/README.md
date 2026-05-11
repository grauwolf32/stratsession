# AppSec source mirrors

Git submodules of the strongest AppSec tools from [`../../TOOLS.md`](../../TOOLS.md). Pinned to the upstream HEAD at clone time; pull updates with `git submodule update --remote <path>`.

## Layout

| Path | Upstream | Category | Note |
|---|---|---|---|
| [`trivy/`](./trivy) | https://github.com/aquasecurity/trivy | SCA / scanner | Default OSS scanner: containers, K8s, IaC, repos, cloud. |
| [`trivy-mcp/`](./trivy-mcp) | https://github.com/aquasecurity/trivy-mcp | SCA / MCP | Trivy as an MCP server. |
| [`defectdojo/`](./defectdojo) | https://github.com/DefectDojo/django-DefectDojo | Vuln management | OWASP DefectDojo. |
| [`sunshine/`](./sunshine) | https://github.com/CycloneDX/Sunshine | SBOM | OWASP CycloneDX SBOM visualizer. |
| [`nettacker/`](./nettacker) | https://github.com/OWASP/Nettacker | DAST / scanner | OWASP Nettacker. |
| [`coraza/`](./coraza) | https://github.com/corazawaf/coraza | WAF | OWASP Coraza (Go-native ModSecurity successor). |
| [`coreruleset/`](./coreruleset) | https://github.com/coreruleset/coreruleset | WAF rules | OWASP CRS. |
| [`patchleaks/`](./patchleaks) | https://github.com/hatlesswizard/patchleaks | Patch analysis | Locates vulnerable code in patch diffs. |
| [`aflplusplus/`](./aflplusplus) | https://github.com/AFLplusplus/AFLplusplus | Fuzzing | The reference greybox fuzzer. |
| [`libafl/`](./libafl) | https://github.com/AFLplusplus/LibAFL | Fuzzing | Modular fuzzer framework. |
| [`ruzzy/`](./ruzzy) | https://github.com/trailofbits/ruzzy | Fuzzing | Coverage-guided Ruby fuzzer. |
| [`vespasian/`](./vespasian) | https://github.com/praetorian-inc/vespasian | API security | API discovery + spec generation. |
| [`hadrian/`](./hadrian) | https://github.com/praetorian-inc/hadrian | API security | YAML-driven API authZ testing. |
| [`electron-safe-updater/`](./electron-safe-updater) | https://github.com/doyensec/ElectronSafeUpdater | Reference design | Secure Electron auto-updater. |
| [`dvbe/`](./dvbe) | https://github.com/infosecak/dvbe | Training | Damn Vulnerable Browser Extension. |
| [`buttercup/`](./buttercup) | https://github.com/trailofbits/buttercup | AI vuln research | Trail of Bits CRS, AIxCC 2nd place. |
| [`seclab-taskflow-agent/`](./seclab-taskflow-agent) | https://github.com/GitHubSecurityLab/seclab-taskflow-agent | AI vuln research | GitHub Security Lab AI vuln-triage framework. |

## Common operations

```bash
# clone everything (after a fresh repo checkout):
git submodule update --init --recursive

# fetch latest upstream on a specific submodule:
git submodule update --remote sources/appsec/trivy

# remove a submodule cleanly:
git submodule deinit sources/appsec/<name>
git rm sources/appsec/<name>
rm -rf .git/modules/sources/appsec/<name>
```

## Out of scope here

The following AppSec-adjacent tools are intentionally not mirrored as submodules — usually because they're K8s/cloud-specific, offensive C2/red-team, or LLM red-team rather than AppSec proper:

- Kubernetes posture / runtime: Spotter, Kyverno, Kubewarden, Copacetic, Falco, Stratoshark, KIEMPossible, HoneyBee.
- Cloud attack: Prowler, CloudFox, MicroBurst, EntraGoat, SAMLSmith, OAuthSeeker, maSSO, ForceHound.
- Identity / AD: BloodHound, AzureHound, MSSQLHound.
- C2 / red team: Empire, Metasploit, C4, Beaconator, GlytchC2, BOAZ, WarHead, Messenger.
- LLM red team: Promptfoo, GARAK, PyRIT, DeepTeam, promptmap, MPIT.
- DFIR / reversing: FLARE-VM, rev.ng, Garuda, Lex Sleuther, mquire, CoBRA, Trailmark.
- Recon / OSINT: Robin, Amass, TheTimeMachine.

If you want any of these mirrored as well, ask — the pattern is identical, just add a new category folder under `sources/`.
