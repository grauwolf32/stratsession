# Trivy-MCP — code-level analysis

A thin Go wrapper that re-exposes the Trivy CLI as an MCP server. Distributed as a Trivy plugin (`trivy plugin install mcp`) and built around `mark3labs/mcp-go v0.43.2`.

## 1. Architecture overview

Single Cobra binary. Entry point is one-shot:

```go
// cmd/trivy-mcp/main.go:14
cmd := commands.NewRootCommand(); return cmd.Execute()
```

The root command (`mcp [flags]`, `pkg/commands/root.go:18`) installs MCP-specific flags (`AddMcpFlags`, `pkg/flag/flag.go:21`), wires SIGINT/SIGTERM cancellation (`pkg/commands/root.go:47`), builds an `mcpserver.McpServer` from parsed `Options`, and calls `server.Start(ctx)`. A sub-command `auth` (`pkg/commands/auth.go:44`) handles Aqua Platform credential lifecycle (login/logout/status/token). There is no scan sub-command — scanning is exposed only via MCP tools.

The whole MCP wiring is ~108 lines (`pkg/mcpserver/mcp.go`); the rest of the repo is finding normalization, the Aqua reporting schema, and a credential store.

## 2. Module / package layout

```
cmd/trivy-mcp/         main.go — Cobra dispatcher
pkg/commands/          root.go, auth.go — Cobra trees
pkg/flag/              flag.go, options.go — global var-backed Cobra flags
pkg/mcpserver/         mcp.go — transport dispatch and lifecycle
pkg/tools/             tool.go — TrivyTools registry
pkg/tools/scan/        scan.go, scan_args.go, aqua.go — three scan tools + handler
pkg/tools/result/      findings.go — findings_list, findings_get tools
pkg/tools/version/     version.go — trivy_version tool
pkg/findings/          finding.go, store.go, list.go, severity.go, id.go — normalized model + LRU store + keyset pagination
pkg/types/             aqua_report.go (~2k LOC of generated structs for Aqua Platform JSON)
pkg/version/           version.go — ldflags-injected version constants
internal/creds/        aqua.go, verify.go — keyring-backed creds, HMAC-signed JWT exchange
```

Distribution glue: `plugin.yaml` (Trivy plugin manifest with 5 OS/arch tarball URIs) and `Makefile` (`install:` target at line 62 copies `plugin.yaml` to `~/.trivy/plugins/mcp/` and builds the binary there).

## 3. MCP protocol implementation

Uses `github.com/mark3labs/mcp-go v0.43.2` (`go.mod:8`) — the community Go SDK, not the official Anthropic one. The server object is constructed once with name + version:

```go
// pkg/mcpserver/mcp.go:47
s := server.NewMCPServer("Trivy MCP Server 🚀", version.Version)
```

Tool registration is uniform: each tool is an `mcp.NewTool(name, ...opts)` value paired with a Go handler of signature `func(ctx, mcp.CallToolRequest) (*mcp.CallToolResult, error)`, then batch-registered via `s.AddTools(tools...)` (`pkg/tools/tool.go:50`, `pkg/tools/tool.go:93`). Request parsing relies on `request.GetArguments()` returning `map[string]any` and is hand-typed (e.g. `pkg/tools/scan/scan_args.go:84`). Responses are emitted with `mcp.NewToolResultText` (`pkg/tools/scan/scan.go:225`) for stringified JSON or `mcp.NewToolResultStructuredOnly` (`pkg/tools/result/findings.go:95,108`) when the result is rich enough to be returned as a structured object.

## 4. Three transports

Single `switch m.Transport` in `pkg/mcpserver/mcp.go:89`:

- `streamable-http` (`mcp.go:90`): `server.NewStreamableHTTPServer(m.Server).Start(addr)` — the addition called out in the brief; uses MCP's Streamable HTTP profile.
- `sse` (`mcp.go:95`): `server.NewSSEServer(m.Server, server.WithBaseURL("http://"+addr), server.WithKeepAlive(true)).Start(addr)`.
- `stdio` (`mcp.go:100`, default per `pkg/flag/flag.go:22`): `server.NewStdioServer(m.Server).Listen(ctx, os.Stdin, os.Stdout)`.

Default host/port is `localhost:23456` (`pkg/flag/flag.go:23-24`). Shutdown is centralized in a goroutine that watches `ctx.Done()` and calls `Shutdown(ctx)` on whichever HTTP/SSE server was started, then `th.Cleanup()` to drop the temp dir (`pkg/mcpserver/mcp.go:69-86`).

## 5. Tools exposed

Six tools are registered in `pkg/tools/tool.go:50-93`:

| Tool name | Defined at | Handler |
|---|---|---|
| `scan_filesystem` | `pkg/tools/scan/scan.go:61` | `ScanTools.ScanWithTrivyHandler` |
| `scan_image` | `pkg/tools/scan/scan.go:76` | same |
| `scan_repository` | `pkg/tools/scan/scan.go:91` | same |
| `findings_list` | `pkg/tools/result/findings.go:16` | `ResultsTools.ListHandler` |
| `findings_get` | `pkg/tools/result/findings.go:38` | `ResultsTools.GetHandler` |
| `trivy_version` | `pkg/tools/version/version.go:30` | `VersionTools.TrivyVersionHandler` |

(`tool.go:54-70` actually registers `ScanFilesystemTool` twice — minor bug, the second `AddTool` likely silently replaces the first inside `mark3labs/mcp-go`.)

The three scan tools share the same arg schema — `target`, `scanType[]` (vuln/misconfig/license/secret), `severities[]`, `outputFormat` (json/cyclonedx/spdx/spdx-json), `fixedOnly`, and a `targetType` const pinned per tool via `targetTypeString("filesystem"|"image"|"repository")` (`pkg/tools/scan/scan_args.go:75`). They all dispatch through one handler.

`ScanWithTrivyHandler` (`pkg/tools/scan/scan.go:107`):
1. Parses args → `scanArgs`.
2. Builds Trivy CLI argv: `[targetType, --scanners=…, --severity=…, --format=…]` (`scan.go:113`), plus `--skip-update` for image scans (`scan.go:126`), `--list-all-pkgs` for JSON+vuln (`scan.go:131`).
3. Branches to `scanWithAquaPlatform` if `--use-aqua-platform` is set and target is filesystem (`scan.go:135`).
4. Writes results to a temp file under `os.TempDir()/trivy-mcp-cache` (`pkg/tools/tool.go:35`, filename per format via `getFilename`, `scan.go:228`).
5. Invokes Trivy either in-process via `commands.NewApp().SetArgs(args); app.Execute()` (`scan.go:158`) — Trivy is a Go dependency in `go.mod`, so by default no fork — or out-of-process via `exec.Command(t.trivyBinary, args...)` when `--trivy-binary` is set (`scan.go:166`).
6. JSON-decodes the file into `trivy/pkg/types.Report`, normalizes via `findings.ReportToFindings` (`pkg/findings/finding.go:111`), stores into the LRU keyed by a UUID `batch_id`, and returns a small `ScanResponse{batch_id, fingerprint, counts, meta, next}` — **not** the full findings. The `Next.Tool="findings_list"` field is a hint to the LLM (`scan.go:215`).

`findings_list` (`result/findings.go:55`) and `findings_get` (`result/findings.go:98`) are the read-through API the LLM is steered toward.

## 6. Trivy plugin wiring

`plugin.yaml` is a stock Trivy plugin manifest: `name: mcp`, `repository`, per-`{os,arch}` selectors pointing to GitHub release tarballs each containing a `./trivy-mcp` binary (`plugin.yaml:9-34`). When the user runs `trivy plugin install mcp`, Trivy's plugin manager fetches the matching tarball, untars to `~/.trivy/plugins/mcp/`, and `trivy mcp …` becomes `exec ~/.trivy/plugins/mcp/trivy-mcp …`.

There is no special handshake — the plugin is a plain CLI. The interesting wiring is the other direction: the plugin re-imports Trivy as a Go library (`github.com/aquasecurity/trivy/pkg/commands`, `pkg/tools/scan/scan.go:17`) and drives it in-process by default, sidestepping a fork per scan. The Trivy version baked in is captured at build time from go.mod and injected as `pkg/version.TrivyVersion` via `-ldflags` (`Makefile:40,67`).

A second nesting appears in the Aqua codepath: `pkg/tools/scan/aqua.go:79` calls `plugin.Run(ctx, "aqua", plugin.Options{Args: args})` — i.e. the MCP plugin shells out (via Trivy's plugin runtime) to the *separate* `aqua` Trivy plugin.

## 7. Aqua Platform integration

Optional, gated on `--use-aqua-platform` (`pkg/flag/flag.go:26`). On boot, `NewMcpServer` calls `creds.Load()` + `Verify()`; failure downgrades silently to OSS mode (`pkg/mcpserver/mcp.go:31-43`).

Credentials are entered via the `auth login` sub-command and persisted as base64(JSON) in the OS keyring under service `trivy-mcp-aqua`, account `aqua-creds`, using `zalando/go-keyring` (`internal/creds/aqua.go:51`). `Verify()` exchanges key+secret for a JWT via HMAC-SHA256-signed POST to `<cspmUrl>/v2/tokens` (`internal/creds/verify.go:103-155`); the JWT is decoded locally to capture `ExpiresAt`. Region picks the URL pair (`internal/creds/aqua.go:20-33`).

When active and target is filesystem, `scanWithAquaPlatform` (`pkg/tools/scan/aqua.go:22`) does NOT call Trivy directly — it sets a fixed env-var bundle (`AQUA_KEY/SECRET`, `CSPM_URL/AQUA_URL`, `AQUA_ASSURANCE_EXPORT=<tmp>/trivy-mcp-scan.assurance.json`, plus `TRIVY_IDE_IDENTIFIER=mcp` and feature toggles `GRADLE=1`, `DOTNET_PROJ=1`, `SAST=1`), then invokes the upstream Aqua Trivy plugin via `plugin.Run(ctx, "aqua", ...)` (`aqua.go:79`). Exit code 13 is treated as success-with-policy-failure (`aqua.go:79`). The assurance file is decoded into `aquatypes.AssuranceReport` (a 2023-line generated struct, `pkg/types/aqua_report.go`) and routed through `findings.AssuranceReportToFindings` (`pkg/findings/finding.go:188`), which also extracts `PolicyResults[].Failed` into `PolicyFailure` objects with deduplication IDs. The list endpoint then injects extra `meta` keys (`policy_alert`, `policy_priority`, etc., `pkg/tools/result/findings.go:90-93`) to steer the LLM.

## 8. Pagination + result framing

Three layers of framing:

1. **Scan response is a stub, not data.** `ScanResponse` (`pkg/tools/scan/scan.go:41`) only returns `batch_id`, content `fingerprint` (SHA-1 over sorted `ID|severity`, `pkg/findings/finding.go:177`), per-artifact-type severity `counts`, `meta`, and a `next` hint pointing at `findings_list`. The LLM never gets the full findings array from a scan call.
2. **Batches live in an in-memory LRU.** `findings.Store` wraps `hashicorp/golang-lru/v2`, capacity 10, keyed by batch UUID (`pkg/findings/store.go:19-36`). Each batch carries pre-sorted findings (severity desc, ID asc) + a `map[ID]int` index for O(1) `findings_get`.
3. **Keyset pagination, base64-cursor.** `findings_list` accepts `limit` (default 100, hard cap 200) and an opaque `token` (`pkg/tools/result/findings.go:31-32`). The cursor is `pageCursor{AfterID, MinSev, Categories, BatchID}` JSON-marshaled and base64-URL-encoded (`pkg/findings/store.go:75-95`). `Store.List` (`store.go:98`) walks the pre-sorted slice, skips until `AfterID`, applies severity-min + category filter, fills up to `limit`, and stamps the new `AfterID` into the next cursor (`store.go:146`).
4. **Compact JSON keys + presentation hints.** `Finding` uses one- or two-character tags (`i`, `c`, `s`, `at`, `an`, `av`, `ap`, `fx`, `fv`, `fc` …, `pkg/findings/finding.go:63-109`) to shrink tokens. To keep the LLM able to read them, `findings_list` returns a schema dictionary in `meta.finding_schema` and `meta.policy_schema` (`result/findings.go:85,93`), plus emoji legends for severity/category and an `action_required`/`presentation_hint` directive — i.e. the prompt is part of the data envelope.

The Streamable HTTP transport adds nothing on top of this — it just changes the byte transport; the chunking is the LLM-side `findings_list` paging above.

## 9. What is genuinely novel at the code level

- **Two-call scan pattern with batch-IDs and keyset cursors instead of returning findings inline** (`pkg/tools/scan/scan.go:202` + `pkg/findings/store.go:98`). Most CLI-MCP wrappers dump the whole scanner output into the tool result, blowing the context window; trivy-mcp answers with a stub and pushes the LLM through a paginated reader, then ships JSON-schema + emoji legends as `meta` so the model can interpret the compact one-character field names. That envelope-as-prompt design is the reusable idea.
- **In-process Trivy + in-process Aqua plugin.** Default scan runs Trivy as a Go library via `commands.NewApp()` (`scan.go:158`); the commercial path then re-enters the Trivy plugin runtime via `plugin.Run(ctx, "aqua", ...)` (`aqua.go:79`). The MCP plugin is itself a Trivy plugin that calls another Trivy plugin — a tidy reuse of Trivy's plugin manager as a scanner dispatch layer rather than reimplementing one.
- **Minimal wrapper footprint.** Excluding the 2k-line generated `aqua_report.go`, the entire MCP surface is well under 1000 LOC; this is effectively the reference template for "wrap a CLI scanner as MCP" — Cobra root, three-line transport switch, six tools, LRU + cursor for paging.
