# 03 · Modern DAST — Caido workflow

**Slide reference**: 9 · **Estimated time**: 30-60 minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md), Caido installed

## Goal

Walk through a Caido-based manual web pentest workflow against OWASP Juice Shop. Demonstrate the 2026 OSS Burp-alternative that's the first credible challenger in 5+ years.

## Tool

| Tool | Submodule |
|---|---|
| **Caido** Community Edition | [`../../sources/perimeter/caido`](../../sources/perimeter/caido) |

> Caido CLI / SDK in the cloned submodule is Rust source. The desktop app is installed separately from caido.io.

## Target

OWASP Juice Shop on `http://localhost:3000` (from scenario 00).

## Scenario A — Proxy setup (5 minutes)

1. Launch Caido desktop app.
2. Create a new project: **File → New Project → "stratlab-juiceshop"**.
3. Configure the upstream proxy listener (default: `127.0.0.1:8443`).
4. Configure your browser to route through the proxy:
   - Firefox: Settings → Network → Manual proxy → HTTP `127.0.0.1:8443`, SOCKS `127.0.0.1:8443`
   - Recommended: install FoxyProxy and create a toggle profile.
5. Install Caido's CA certificate in the browser to avoid TLS warnings (download from `http://127.0.0.1:8443/` while proxy is on).

Verify: visit `http://localhost:3000` — request should appear in Caido's HTTP History pane.

## Scenario B — Sitemap + interception (10 minutes)

1. **Browse Juice Shop normally** for 2-3 minutes — log in as `admin@juice-sh.op / admin123` (default), browse products, place an item in cart.
2. **Sitemap tab**: shows automatically-built tree of all requested paths.
3. **HTTP History tab**: every request/response is logged. Filter by host, status code, content type.
4. **Intercept tab**: pause incoming traffic for live modification.

## Scenario C — Replay + Repeater workflow (10 minutes)

Replicate Burp Repeater workflow:

1. Right-click any request in HTTP History → **Send to Replay**.
2. Modify the request body / headers in the editor.
3. Click **Send** — response appears in adjacent pane.
4. Use the **Diff** feature to compare responses across replays.

Example: try changing the `userId` parameter in a product-review GET request from `1` to `2`, `3`, `4`… see whose data leaks (this is a BOLA vuln in Juice Shop).

## Scenario D — Match-and-replace (5 minutes)

Caido's MATCH-AND-REPLACE rules apply transformations on every outbound request. Pattern: auto-inject auth token, modify user-agent, etc.

1. **Project → Workflows → Match & Replace**.
2. Create rule:
   - Match: `Authorization: Bearer .*`
   - Replace: `Authorization: Bearer attacker_token_here`
3. Browse the app — all requests now use the substituted header.

This is the "test multi-user access at scale" pattern that Hadrian automates programmatically.

## Scenario E — Workflows (Caido's signature feature) (15 minutes)

**Workflows** = Caido's named-and-saved request modification pipelines. Roughly equivalent to Burp's "macros" but more powerful.

1. **Workflows tab → New Workflow**.
2. Add steps:
   - **Step 1**: HTTP request (any endpoint that returns a JSON token)
   - **Step 2**: Extract `data.token` from the response
   - **Step 3**: Use extracted token as `Authorization: Bearer {{step1.data.token}}` in the next request
3. Run the workflow — each step runs in sequence, with data flowing between them.

This solves the **"login → get token → use token in next request"** pattern manually, before/instead of using an automated authZ tool like Hadrian.

## Scenario F — Caido vs Burp — what's actually new

For the slide-9 talking-track, the diff vs Burp Community is:

| Feature | Burp Suite Community | Caido CE |
|---|---|---|
| Active scanner | ❌ (Pro-only) | ❌ (Pro-only) — Caido Pro tier |
| Repeater | ✅ | ✅ |
| Intruder / fuzzing | ❌ (Pro-only) | ✅ via Workflows |
| Match-and-replace rules | ✅ but limited | ✅ + scripting |
| Workflow / macro | Limited | First-class |
| WebSocket support | ✅ | ✅ |
| Performance on large sessions | Slow (Java) | Fast (Rust) |
| Plugin ecosystem | Massive (BApp Store) | Small but growing |
| UX | Functional, dated | Modern, dark mode |
| License | Commercial freemium | Open-source CE + commercial Pro |

The Burp plugin ecosystem is still a big gap. For 90% of common pentest tasks, Caido CE matches or exceeds Burp Community.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Browser can't reach Juice Shop through proxy | CA cert not trusted | Re-import Caido CA into browser keystore |
| Caido GUI is slow on large session | Default settings too generous | Settings → reduce history retention to last 1000 requests |
| Workflow doesn't extract value | JSONPath selector wrong | Test selector in DevTools Console with `JSON.parse(response).path.to.field` first |
| Plugin missing | Burp plugin needed | No equivalent in Caido yet; common gap, document the gap in slide 26 (risks) |

## Sources

- Caido docs: https://docs.caido.io (verify against installed version)
- Repo: `sources/perimeter/caido` (v0.56.0 pinned)

## Live demo recommendation

**Don't live-demo Caido** on slide 9 unless you've rehearsed exactly this scenario E flow 3+ times — UIs with auth flows are unreliable on stage. Pre-record a 30-second walkthrough showing:
- Browser → proxy → request appears in History
- Right-click → Send to Replay → modify → Send
- Show workflow with token-extraction

If you must live-demo: Scenario A (5 min) is the lowest-risk. Skip workflow.
