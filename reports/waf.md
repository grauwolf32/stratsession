# WAF — Coraza · OWASP Core Rule Set

These two are not competitors — they are **engine** and **rules**. But the design of each is interesting individually and the way they interlock signals the future of the open WAF stack.

| | Coraza | OWASP Core Rule Set (CRS) |
|---|---|---|
| What | WAF engine | Rule set for WAF engines |
| Language | Go | SecLang (ModSecurity rule language) |
| OWASP status | OWASP **Production** project | OWASP **Flagship** project |
| First release | 2022 | 2010 (forked from ModSecurity rules) |
| Compatibility | ModSecurity SecLang | ModSecurity, Coraza, any SecLang-compliant engine |
| Repo size | 4 MB / 63 files | 6.5 MB / 256 files |

## Coraza — Go-native ModSecurity successor

The novelty: **Coraza is the first production-quality re-implementation of ModSecurity since the original C engine entered maintenance mode.** Trustwave handed ModSecurity over to OWASP in 2024, and the C engine is winding down. Coraza is positioned as the migration path.

What's actually novel:

1. **100% CRS v4 compatibility, not 99%.** Look at the badge: `Coreruleset Compatibility 100%`. Most ModSec replacements implement *most* of SecLang; Coraza implements all of CRS's exercised surface.
2. **Library-first architecture.** ModSecurity is a server module (`mod_security2.so`). Coraza is a Go library you embed:
   ```go
   waf, _ := coraza.NewWAF(coraza.NewWAFConfig().WithDirectives(`SecRule ...`))
   tx := waf.NewTransaction()
   tx.ProcessConnection(...)
   if it := tx.ProcessRequestHeaders(); it != nil { ... }
   ```
   This composes into anything: HTTP servers, reverse proxies, middleware, sidecars, service mesh filters, **Proxy-Wasm** plugins for Envoy.
3. **Wasm deployment.** The [`coraza-proxy-wasm`](https://github.com/corazawaf/coraza-proxy-wasm) plugin runs Coraza inside any Proxy-Wasm-capable proxy (Envoy, Istio, etc.) as a sandboxed Wasm filter. This is a deployment shape ModSecurity could never reach.
4. **Build-tag-driven specialization.** Look at the README's `Build tags` section — at compile time you can:
   - Disable individual operators (`coraza.disabled_operators.*`) to shrink the binary.
   - Enable **multiphase evaluation** (`coraza.rule.multiphase_evaluation`) — rule variables evaluate in the phases they become ready, not just the phase the rule is declared in. This is *new behavior* not present in ModSecurity.
   - Toggle memoization (`coraza.no_memoize`) — Coraza caches compiled regex and aho-corasick patterns globally across WAF instances. Material for long-lived processes with frequent live reloads.
   - **`@rx` pre-filter** (`coraza.rule.rx_prefilter`) — skip the full regex if a cheap pre-check rules out a match. Pure performance optimization.
   - `no_fs_access` — for sandboxed environments with no filesystem access (Wasm, embedded).
   - `coraza.rule.case_sensitive_args_keys` — RFC 3986-compliant ARGS handling. Becomes the default in the next major version.
   - `coraza.rule.no_regex_multiline` — aligns with CRS expectations. Becomes default in the next major version.
5. **Multiple integrations as separate repos**, all under `corazawaf/`:
   - `coraza-caddy` — Caddy plugin
   - `coraza-proxy-wasm` — Envoy/Istio Wasm
   - `coraza-spoa` — HAProxy SPOE
   - `libcoraza` — C library for nginx integration
   - `RuiQi WAF` — third-party web management panel
6. **`http/e2e/`** — Coraza ships an end-to-end test harness as a library you can run against any WAF deployment, not just Coraza. `go run github.com/corazawaf/coraza/v3/http/e2e/cmd/httpe2e@main --proxy-hostport localhost:8080 --httpbin-hostport localhost:8081`. **Vendor-neutral WAF correctness testing as an artifact.**

What's *not* novel: SecLang itself. Coraza is deliberately a re-implementation, not a redesign. The OWASP CRS team's next-generation rule language work (announced at OWASP USA 2025) is the future SecLang successor.

## OWASP Core Rule Set — the de-facto attack-pattern library

The CRS is **the** open ruleset for SecLang-compatible WAFs. Everything anywhere that talks ModSecurity uses some flavor of CRS. The novelty in 2026 is less about the rules themselves and more about how the project structures them.

Rule files by category (from `rules/`):

| Phase | File | Topic |
|---|---|---|
| Init | `REQUEST-901-INITIALIZATION` | Engine setup |
| 905 | `REQUEST-905-COMMON-EXCEPTIONS` | Pre-block exceptions |
| 911 | `REQUEST-911-METHOD-ENFORCEMENT` | Method allowlists |
| 913 | `REQUEST-913-SCANNER-DETECTION` | sqlmap / nikto / etc. |
| 920 | `REQUEST-920-PROTOCOL-ENFORCEMENT` | HTTP/1.1 protocol violations |
| 921 | `REQUEST-921-PROTOCOL-ATTACK` | Request smuggling, etc. |
| 922 | `REQUEST-922-MULTIPART-ATTACK` | multipart/form-data attacks |
| 930 | `REQUEST-930-APPLICATION-ATTACK-LFI` | Local file inclusion |
| 931 | `REQUEST-931-APPLICATION-ATTACK-RFI` | Remote file inclusion |
| 932 | `REQUEST-932-APPLICATION-ATTACK-RCE` | Remote code execution |
| 933 | `REQUEST-933-APPLICATION-ATTACK-PHP` | PHP-specific attacks |
| 934 | `REQUEST-934-APPLICATION-ATTACK-GENERIC` | Generic injection patterns |
| 941 | `REQUEST-941-APPLICATION-ATTACK-XSS` | Cross-site scripting |
| 942 | `REQUEST-942-APPLICATION-ATTACK-SQLI` | SQL injection |
| 943 | `REQUEST-943-APPLICATION-ATTACK-SESSION-FIXATION` | Session attacks |
| 944 | `REQUEST-944-APPLICATION-ATTACK-JAVA` | Java-specific attacks |
| 949 | `REQUEST-949-BLOCKING-EVALUATION` | Anomaly scoring → block decision |
| RESP | `RESPONSE-950..956` | Data leakage detection in responses (SQL errors, Java stacks, PHP errors, IIS errors, web shells, Ruby) |
| RESP | `RESPONSE-959-BLOCKING-EVALUATION` | Response-side block evaluation |
| RESP | `RESPONSE-980-CORRELATION` | Final correlation / scoring |

What's actually novel about CRS in 2026:

1. **Paranoia levels** — CRS organizes rules into four `paranoia_level` tiers (1=loosest, 4=tightest). Most other rulesets are binary (on/off). PL is a knob you can crank per-application based on its tolerance for false positives. This is a *programmatic* approach to FP/FN tradeoff.
2. **Anomaly scoring** — every rule contributes a numeric score. The final blocking decision (file 949) compares the accumulated score against thresholds. This is fundamentally different from ModSecurity defaults (rule-by-rule deny). It lets you tune the *aggregate sensitivity* without disabling specific rules.
3. **Regex Assembly (`regex-assembly/`)** — CRS uses [`crs-toolchain`](https://github.com/coreruleset/crs-toolchain) to *generate* regexes from declarative source files. You don't write the giant alternation by hand; you list patterns, and the toolchain assembles, optimizes, and prepends them to the rule. This is a non-obvious quality-of-life win and the reason CRS regex changes are reviewable as patches.
4. **`tests/` is golden** — CRS ships a comprehensive [go-ftw](https://github.com/coreruleset/go-ftw) regression test suite that any compatible engine can run against itself. This is *executable specification* of what a SecLang engine is expected to do.
5. **AI-content data files** — `ai-critical-artifacts.data` appears in the data files list, indicating CRS is starting to add AI-attack-class detection. New territory for the project; minimal documentation yet.
6. **Next-generation rule language announced at OWASP Global AppSec USA 2025** — Felipe Zipitría's session "Towards the next generation OWASP CRS ruleset language" signaled CRS may not stay on SecLang forever. Coraza's Go architecture makes this practical: Coraza could implement the new language while keeping SecLang compatibility.

## Why this matters together

Coraza + CRS is the **only fully OSS WAF stack with active development in 2026.** ModSecurity's C engine is winding down, NAXSI is dormant, commercial WAFs are closed. If you want to deploy a WAF and not lock yourself into a vendor, the Coraza/CRS combination is currently the only sustainable choice.

Strategic implications:

1. **Service-mesh-native WAFs are viable now.** Drop `coraza-proxy-wasm` into Istio/Envoy and you have CRS-enforced filtering at every hop. ModSecurity could never do this.
2. **WAFs as embedded libraries are viable now.** `coraza` is `go get`-able into any Go HTTP service. You can ship "this service has its own WAF layer" without a sidecar.
3. **The CRS next-gen rule language is the place to watch.** When CRS commits to a new language, Coraza will likely be the first engine to implement it, because the same authors collaborate across both projects.
4. **AI-attack rules are nascent.** The `ai-critical-artifacts.data` file is a tiny seed of what will likely become an AI-specific rule track. Worth watching the CRS roadmap for prompt-injection / model-extraction signature work.

## Adoption pattern that actually works

For most teams:

1. **Deploy Coraza + CRS PL=1 in monitor-only mode** in your reverse proxy (Caddy or Envoy/Wasm).
2. **Watch logs for two weeks**, tune exception rules for legitimate-but-flagged traffic.
3. **Raise to PL=2 and switch to enforce mode** on lower-risk endpoints.
4. **Add a custom rule file (`REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf`)** for application-specific allowlists.
5. **Run `go-ftw` against your deployed instance** weekly to catch regressions.

This is the only WAF deployment pattern with both *open* tooling and *active* maintenance through 2026.
