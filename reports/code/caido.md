# Caido — code-level analysis

## TL;DR (must read before reading the rest)

**Caido is not open source.** The public `caido/caido` repository — vendored here at `sources/perimeter/caido/` — contains only branding assets, GitHub Actions issue-triage automation, issue templates, a security policy, and a README. There is no `Cargo.toml`, no Rust workspace, no Vue/TS frontend source, no proxy crate, no SDK crate. A full directory listing of the submodule:

```
brand/   prompts/   scripts/   .github/   README.md   SECURITY.md
```

This is a meaningful correction to the brief — Caido has been positioned in `reports/perimeter-stack.md` and `TOOLS.md` as a "Rust Burp-alternative," and that framing is correct as a *product* description, but **the source is not on GitHub**. Code-level architectural claims about Caido elsewhere in this brief should be marked as based on docs/binary inspection rather than source review. The only source-grounded architectural facts available below come from the triage-bot prompts and the security policy.

## 1. Workspace overview

No `Cargo.toml` exists in the repository. The Rust crates Caido ships in its binary releases are not published here. The closest architectural disclosure in-tree is the triage-bot system prompt at `sources/perimeter/caido/prompts/triage.md:8-32`, which enumerates the *labelable* components rather than crate names:

- **CLI** — split into a *Frontend* ("all user interface elements and interactions") and a *Backend* ("core application logic and processing"). The triage prompt explicitly says these "work together to form the complete CLI experience" (`prompts/triage.md:14-18`).
- **Desktop** — described as "a wrapper around the CLI" with a connection manager that lets users spawn instances (`prompts/triage.md:20-24`). This implies the desktop binary embeds or spawns the CLI rather than re-linking the backend crates.
- **Dashboard** — a separate cloud product split into `dashboard` (UI) and `cloud` (backend) (`prompts/triage.md:26-31`). Out of scope for a perimeter brief.
- **Extension** — a browser extension that configures the browser to talk to a Caido instance (`prompts/triage.md:33-34`). This is a thin proxy-config helper, not the intercept engine.

No crate boundaries, no `members = [...]`, no feature flags can be cited from the repo.

## 2. Module layout

The README is marketing-only (`README.md:1-40`) and reveals nothing structural. The triage prompt's component split (above) is the only first-party signal: a two-tier CLI (frontend ↔ backend) with the desktop binary acting as a launcher/wrapper. Whether the frontend is Vue, React, or Svelte; whether the desktop wrapper is Tauri, Electron, or a custom Rust shell; whether the backend is Tokio + Hyper or Axum — none of this can be cited from any file in the submodule.

## 3. Proxy intercept core

Not present in the repository. No `.rs` file ships in `sources/perimeter/caido/`. No CA-cert generation code, no TLS MITM handler, no request/response model, no replay queue can be inspected.

The only architectural fact about the proxy that the public repo discloses is *indirect*, from `SECURITY.md:35-43`: Caido considers vulnerabilities requiring "code execution on the host system" out of scope, which implies (but does not prove) that the intercept core trusts its host process and runs without a sandbox layer between proxy and OS.

## 4. Project storage

Not disclosed in any in-tree file. No schema, no migrations directory, no `.sql`, no SQLite/SeaORM/Diesel artifact, no on-disk format spec.

## 5. Plugin / workflow SDK boundary

This is the single subsystem the public repo *does* meaningfully document — but only in policy form, not in code. `SECURITY.md:30-39` states verbatim:

> Due to the flexible nature of our plugin system, plugins in Caido have unrestricted access within the environment. This includes the ability to:
> - Access files on your computer.
> - Connect to the internet.
> - Install or execute additional programs.
>
> **Important Note**: This is a known limitation of the plugin system that cannot be fully restricted at this time.

Concretely: plugins are **not Wasm-sandboxed**. If they were running in Wasmtime/Wasmer with capability-based imports, file/network/exec access would be opt-in via host functions and the security note would not need to exist. The "cannot be fully restricted at this time" phrasing is consistent with either a native dynamic-library plugin model or an embedded JS/TS runtime (e.g. Boa, QuickJS, Deno core) that exposes unrestricted host bindings. Without code we cannot pick between those; both are consistent with the policy. The `.github/ISSUE_TEMPLATE/plugin.md` template treats plugins as community-author submissions (`plugin.md:1-22`), reinforcing that the SDK boundary is permissive by design.

## 6. Backend ↔ frontend transport

Not disclosed. The triage prompt only says the two "work together" (`prompts/triage.md:18`). No GraphQL schema (`.graphql`), no OpenAPI spec, no `.proto`, no Tauri `invoke` handler list ships in this repo. Caido's public docs site is known to publish a GraphQL schema for its SDK, but that file is not in this submodule and therefore cannot be cited per the hard rules.

## 7. Tauri bundling

Cannot be confirmed from the repo. No `tauri.conf.json`, no `src-tauri/`, no `Cargo.toml [package.metadata.bundle]`. The desktop wrapper described at `prompts/triage.md:20-24` could equally be Tauri, a hand-rolled webview shell, or an Electron-style packager. The brand assets in `brand/svg/` (e.g. `logo.svg`, `logo_name.svg`, `name.svg`) are the only desktop-app artifacts present and they are pure visual identity, not packaging metadata.

## 8. Notable performance choices

Cannot be evaluated. No async runtime selection, no mmap vs in-memory request-store strategy, no streaming-body handling, no connection-pool sizing can be cited from any file in `sources/perimeter/caido/`.

## 9. What's genuinely novel at the code level

Cannot be assessed from this repository. The only design choice the public repo lets us identify with confidence is a *negative* one: Caido has explicitly chosen **not** to sandbox its plugin runtime (`SECURITY.md:30-39`), trading off the Wasm-isolation approach taken by newer entrants for a Burp-style "trust the plugin author" model. Whether the proxy core, project store, or transport layer contain anything novel cannot be determined without access to the actual Rust source, which the vendor does not publish.

## Recommendation for the parent brief

Update `reports/perimeter-stack.md` to flag Caido as **source-unavailable**: the GitHub repo `caido/caido` is a public-facing issue tracker and brand repo, not the product source. Code-level architectural claims about Caido in the stratsession brief should be marked as based on docs/binary inspection rather than source review, or sourced from a separate reverse-engineering pass on the shipped `caido` binary (out of scope here). The one source-grounded architectural fact worth carrying forward is the explicit no-sandbox plugin model documented at `sources/perimeter/caido/SECURITY.md:30-43`, which is a meaningful security-posture differentiator versus Wasm-sandboxed competitors.
