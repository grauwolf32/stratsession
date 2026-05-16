# CI/CD pipeline security source mirrors

Git submodules of the **2026 wave** of CI/CD security tooling — the attack/defense pair that emerged in the wake of the **TeamPCP incident (March 2026)**, which compromised Trivy, LiteLLM, KICS, Telnyx, and dozens of npm packages through GitHub Actions workflow injection.

See [`../../reports/ci-cd-security.md`](../../reports/ci-cd-security.md) for the per-tool deep-dive.

## Layout

| Path | Upstream | Side | Note |
|---|---|---|---|
| [`smokedmeat/`](./smokedmeat) | https://github.com/boostsecurityio/smokedmeat | Offensive | First OSS red-team framework purpose-built for CI/CD pipelines. AGPL-3.0. From Boost Security Labs (makers of `poutine`). Ships with the Whooli deliberately-vulnerable training org. **(new 2026)** |
| [`plumber/`](./plumber) | https://github.com/getplumber/plumber | Defensive | GitLab-first (and GitHub-second as of v0.3.0) CI/CD compliance scanner. MPL-2.0. One Rego engine across both providers; emits PBOM + CycloneDX. **(new 2026)** |

## Cross-list

- **Brutus** ([`../perimeter/brutus`](../perimeter/brutus)) is the credential-validation tool that pairs naturally with SmokedMeat — once SmokedMeat extracts secrets from a runner, Brutus is what tells you where those secrets work.

## Common operations

```bash
# clone everything (after a fresh repo checkout)
git submodule update --init --recursive

# fetch latest upstream on a specific submodule
git submodule update --remote sources/ci-cd/smokedmeat

# remove a submodule cleanly
git submodule deinit sources/ci-cd/<name>
git rm sources/ci-cd/<name>
rm -rf .git/modules/sources/ci-cd/<name>
```

## Recent CI/CD tools worth knowing about (not mirrored here)

If you want any of these added as well, ask — pattern is identical:

- **[poutine](https://github.com/boostsecurityio/poutine)** — SAST scanner for GitHub Actions / GitLab CI; embedded inside SmokedMeat. Worth pulling separately if you want the SAST without the C2.
- **[zizmor](https://github.com/woodruffw/zizmor)** — William Woodruff's GitHub Actions SAST; complements poutine.
- **[Gato-X](https://github.com/AdnaneKhan/Gato-X)** — Adnan Khan's GitHub Actions enumeration / abuse toolkit; the offensive vocabulary that SmokedMeat operationalizes.
- **[Nord-Stream](https://github.com/synacktiv/nord-stream)** — Synacktiv's CI/CD secret-extraction tool; the original "scrape runner memory" research.
- **[Legitify](https://github.com/Legit-Labs/legitify)** — GitHub posture scanner; commercial-leaning but the CLI is OSS.
- **[pinact](https://github.com/suzuki-shunsuke/pinact)** — pins GitHub Actions references to SHAs; minimal but high-impact defensive primitive.
