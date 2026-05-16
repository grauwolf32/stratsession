# Cloud posture source mirrors

Git submodule for AWS-focused posture tooling. See [`../../reports/cloud-posture.md`](../../reports/cloud-posture.md) for the deep-dive.

## Layout

| Path | Upstream | Note |
|---|---|---|
| [`cloud-audit/`](./cloud-audit) | https://github.com/gebalamariusz/cloud-audit | Opinionated AWS-only scanner (94 checks across 23 services). Attack-chain correlation, IAM escalation graph (61 methods), what-if simulator, AI-SPM checks, MCP server. MIT. **(new 2026)** |

## Cross-list

- **Trivy** ([`../appsec/trivy`](../appsec/trivy)) — cross-cloud / container / IaC scanner that complements `cloud-audit`'s AWS-specific depth.
- **Cloud-audit threat-feed** carries references to research from Wiz, Datadog Security Labs, Unit 42, Permiso — pair with the cloud-native blogs in [`../../blogs/cloud-native.md`](../../blogs/cloud-native.md).

## Recent cloud tools worth knowing about (not mirrored here)

Pattern is identical — ask if you want any of these added:

- **[Prowler](https://github.com/prowler-cloud/prowler)** — the AWS / multi-cloud reference scanner; 572 checks across 83 AWS services + 13 other providers. Use for breadth + compliance; use `cloud-audit` for depth + remediation.
- **[Pacu](https://github.com/RhinoSecurityLabs/pacu)** — AWS exploitation framework; offensive counterpart.
- **[CloudFox / CloudFoxable](https://github.com/BishopFox/cloudfox)** — Bishop Fox's AWS situational-awareness toolkit.
- **[KIEMPossible](https://github.com/PaloAltoNetworks/KIEMPossible)** — Kubernetes IAM entitlement manager from Palo Alto.
- **[ScubaGear](https://github.com/cisagov/ScubaGear)** / **[ScubaGoggles](https://github.com/cisagov/ScubaGoggles)** — CISA baselines for M365 / Google Workspace.
- **[pathfinding.cloud](https://github.com/DataDog/pathfinding.cloud)** — Datadog's academic underpinning that inspired `cloud-audit`'s attack-chain layer.

## Common operations

```bash
git submodule update --init --recursive
git submodule update --remote sources/cloud/cloud-audit
git submodule deinit sources/cloud/<name>
git rm sources/cloud/<name>
rm -rf .git/modules/sources/cloud/<name>
```
