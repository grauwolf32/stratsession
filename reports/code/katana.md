# Katana — code-level analysis

## 1. Architecture overview

The binary entry point is `cmd/katana/main.go` and is mostly flag plumbing: `readFlags()` builds a `goflags.FlagSet` populating a single `*types.Options` (`cmd/katana/main.go:30`, `cmd/katana/main.go:132`), then calls `runner.New(options)` (`cmd/katana/main.go:64`) and `katanaRunner.ExecuteCrawling()` (`cmd/katana/main.go:112`). A `SIGINT` handler serialises in-flight URLs into a JSON resume file under `~/.config/katana/resume-<xid>.cfg` (`cmd/katana/main.go:82`, `cmd/katana/main.go:283`).

`internal/runner/runner.go` is the assembly point. `Runner` (`internal/runner/runner.go:27`) owns one `engine.Engine`, a `*types.CrawlerOptions`, a `RunnerState{InFlightUrls *SyncLockMap}` for resume, and a `*networkpolicy.NetworkPolicy` for `--exclude` (cdn/private-ips/CIDR/ASN/port) (`internal/runner/runner.go:111`). The engine choice is a single switch on the options (`internal/runner/runner.go:95`):

```go
switch {
case options.ChromeWSUrl != "":
case options.Headless:        crawler, err = headless.New(crawlerOptions)
case options.HeadlessHybrid:  crawler, err = hybrid.New(crawlerOptions)
default:                       crawler, err = standard.New(crawlerOptions)
}
```

The per-target loop lives in `internal/runner/executer.go:13`: it parses inputs, marks each as in-flight, then runs `r.crawler.Crawl(input)` inside a `sizedwaitgroup.New(r.options.Parallelism)` (`internal/runner/executer.go:32`). Parallelism is *across targets*; concurrency *within* a target is the engine's job.

The output sink is an interface (`pkg/output/output.go:37`):

```go
type Writer interface { Close() error; Write(*Result) error; WriteErr(*Error) error }
```

The default implementation `StandardWriter` (`pkg/output/output.go:46`) is constructed in `types.NewCrawlerOptions` (`pkg/types/crawler_options.go:128`) and is the *only* exit path — every engine calls `s.Options.OutputWriter.Write(...)` via `Shared.Output` (`pkg/engine/common/base.go:221`). Optionally a user-provided `OnResult` callback fires after a successful write (`pkg/engine/common/base.go:236`).

## 2. Module / package layout

- `cmd/katana/` — flag parsing and main loop.
- `internal/runner/` — engine selection, network policy, resume, signal handling.
- `pkg/types/` — `Options` (CLI surface, `pkg/types/options.go`) and `CrawlerOptions` (assembled resources: parser, scope manager, dialer, rate limiter, wappalyzer, dit classifier, output writer; `pkg/types/crawler_options.go:24`).
- `pkg/navigation/` — the `Request`/`Response` value types passed between engine, parser and output.
- `pkg/engine/` — `engine.Engine` interface (`pkg/engine/engine.go:3`) plus `common/` (shared crawl loop, HTTP client, backoff), `standard/`, `hybrid/`, `headless/`, `parser/` (response → links).
- `pkg/output/` — `Writer` interface plus JSON / screen / template formatters, per-host store, custom-field regex.
- `pkg/utils/parser/` does **not exist** — link parsers live under `pkg/engine/parser/parser.go`. HTML helpers (`ParseSRCSetTag`, `ParseLinkTag`, `ParseRefreshTag`, `ExtractRelativeEndpoints`) sit in `pkg/utils/utils.go`, jsluice integration in `pkg/utils/jsluice.go`, and form fill in `pkg/utils/formfields.go`.
- `pkg/utils/scope/` — DNS + URL scope manager.
- `pkg/utils/queue/` — pluggable BFS/DFS queue (`pkg/utils/queue/queue.go:20`).
- `pkg/utils/filters/` — unique URL/content hybrid-store filter (`pkg/utils/filters/simple.go:23`) and cycle detection.
- `pkg/utils/extensions/`, `pkg/utils/pathtrie.go`, `pkg/utils/urlfingerprint.go` — extension filtering and "similar URL" fingerprinting via path-position cardinality (`-fsu`).

## 3. Standard vs headless engine — the central decision

The `engine.Engine` contract is two methods (`pkg/engine/engine.go`):

```go
type Engine interface { Crawl(string) error; Close() error }
```

Three engines satisfy it: `standard` (`pkg/engine/standard/standard.go:11`), `hybrid` (`pkg/engine/hybrid/hybrid.go:22`), and the newer pure `headless` (`pkg/engine/headless/headless.go:22`). All three compose `*common.Shared` (`pkg/engine/common/base.go:48`) for cookie jar, known-files DB, path-trie, per-host backoff cache (`golang-lru` capped at 10 000 hosts, `pkg/engine/common/base.go:46`) and the `Enqueue` pipeline.

**Standard** (`pkg/engine/standard/standard.go:30`) builds a `retryablehttp.Client` via `common.BuildHttpClient` (`pkg/engine/common/http.go:23`) — `fastdialer`-backed transport with optional JA3 client-hello randomisation (`pkg/engine/common/http.go:29`) and Burp-aware TLS 1.2 cap (`pkg/engine/common/http.go:47`). `makeRequest` (`pkg/engine/standard/crawl.go:22`) does a single round-trip, limit-reads the body to `BodyReadSize` (`pkg/engine/standard/crawl.go:95`), hashes for unique-content de-dup, runs Wappalyzer fingerprint and dit knowledge-base classification, parses with `goquery` and returns a `navigation.Response`. The loop is `common.Shared.Do` (`pkg/engine/common/base.go:405`), bounded by `sizedwaitgroup.New(Concurrency)`.

**Hybrid** (`pkg/engine/hybrid/hybrid.go:37`) launches a Chrome via `go-rod/launcher`, opens an incognito context, and gives each request its own `rod.Page`. The hybrid engine *overrides* `Do` (`pkg/engine/hybrid/hybrid.go:150`) to be **sequential** — comment at line 145 spells out that CDP cannot safely be driven by parallel goroutines against one browser. So `Concurrency` only applies to the standard engine; hybrid serialises.

The third engine `headless` (`pkg/engine/headless/headless.go:96`, ~3 000 LOC under `pkg/engine/headless/`) is a more ambitious rewrite with its own crawler/state machine, captcha solver registry (`pkg/engine/headless/captcha/`), graph (`pkg/engine/headless/graph/graph.go`), browser-pool, stealth and an internal debugger HTTP server on :8089 (`pkg/engine/headless/headless.go:45`). It is selected by `-hl` or by attaching to an external browser via `-cwu` / `ChromeWSUrl`. It deliberately bypasses `common.Shared.Do`.

## 4. go-rod integration (hybrid engine)

Launcher config is built in `buildChromeLauncher` (`pkg/engine/hybrid/hybrid.go:267`): `Leakless(true)`, disable-gpu / certificate-errors / notifications, fixed 1080×1920 viewport, user-data-dir under a temp directory (or `--chrome-data-dir`), optional system binary via `launcher.LookPath()` (`pkg/engine/hybrid/hybrid.go:285`), and headless-options `-ho k=v` mapped into rod flags (`pkg/engine/hybrid/hybrid.go:314`).

Per request lifecycle in `pkg/engine/hybrid/crawl.go:30`:

1. `s.Browser.Page(proto.TargetCreateTarget{})` opens a new tab; two contexts are layered — session ctx and a per-request timeout (`pkg/engine/hybrid/crawl.go:46`).
2. A `Hijack` (`pkg/engine/hybrid/hijack.go:11`) enables `Fetch.enable` with `URLPattern:"*"`, `RequestStage:Response` (`pkg/engine/hybrid/hijack.go:31`). Every paused request is converted into a synthetic `http.Request`/`http.Response` (`pkg/engine/hybrid/crawl.go:88-120`), fed through `parser.ParseResponse` and re-enqueued — this is how sub-resource and XHR URLs enter the queue. The body is pulled via `Fetch.getResponseBody` (`pkg/engine/hybrid/hijack.go:71`) and the request is then `Fetch.continueRequest`ed (`pkg/engine/hybrid/hijack.go:92`).
3. XHR/Fetch/Script resource types are captured into `xhrRequests` when `-xhr` is set (`pkg/engine/hybrid/crawl.go:151`).
4. A frame-navigation listener subscribes to `Page.frameNavigated` to discover JS redirects (`pkg/engine/hybrid/crawl.go:205`).
5. Navigation is `page.Navigate(url)` plus a `WaitNavigation` chosen by `-page-load-strategy` (`load`/`domcontentloaded`/`networkidle` mapped to `firstMeaningfulPaint`, etc.) (`pkg/engine/hybrid/crawl.go:217-229`), followed by `page.WaitStable(timeStable)`.
6. CDP element interaction: `page.Elements("a[onclick]")` and `link.Click(proto.InputMouseButtonLeft, 1)` simulate clicks to surface JS-only navigation, comparing URL before/after via `page.Info()` (`pkg/engine/hybrid/crawl.go:280`).
7. Shadow-DOM extraction uses `DOM.getDocument` with `Pierce: true, Depth: -1` (`pkg/engine/hybrid/crawl.go:346`) and `traverseDOMNode` (`pkg/engine/hybrid/crawl.go:455`) walks `ShadowRoots`, `TemplateContent`, `PseudoElements` and rebuilds a pseudo-HTML doc that is re-parsed and re-enqueued.

## 5. Scope rules

`pkg/utils/scope/scope.go:14` defines `Manager` with two regex sets (`inScope`, `outOfScope`) plus a `dnsScopeField` enum: `dn`, `rdn`, `fqdn`, or `customDNSScopeField` for any other string (compiled as a regex against the hostname) (`pkg/utils/scope/scope.go:24, 43`). `Validate` (`pkg/utils/scope/scope.go:72`) gates DNS scope first (skipped when `--no-scope`) and then the URL regex set: `outOfScope` short-circuits to reject, `inScope` (if non-empty) must match.

`validateDNS` (`pkg/utils/scope/scope.go:120`) routes by field: `fqdn` and IP literals require exact case-insensitive match against `rootHostname`; otherwise `getDomainRDNandRDN` (`pkg/utils/scope/scope.go:149`) uses `golang.org/x/net/publicsuffix` to split the root domain, then `dn` does `strings.Contains(hostname, dn)` and `rdn` does `strings.HasSuffix(hostname, rdn)` (`pkg/utils/scope/scope.go:138-141`).

Scope is the *last* filter in `Shared.Enqueue` (`pkg/engine/common/base.go:155`); rejected items are dropped, or if `-do/display-out-scope` is set they are emitted as out-of-scope output without being visited (`pkg/engine/common/base.go:159`).

## 6. Parsers

`pkg/engine/parser/parser.go:37` registers a static list of 26+ body parsers and 3 header parsers. Each is a `ResponseParserFunc func(*navigation.Response) []*navigation.Request`. Tags covered: `a[href|ping]`, `link[href]`, `script[src]`, `img[src|srcset|dynsrc|longdesc|lowsrc]`, `iframe[src|srcdoc]`, `object[data|codebase|param]`, `svg image/script`, `video/audio/track/source`, `body[background]`, `table[background]`, `applet[archive|codebase]`, `embed`, `frame`, `base[href]`, `meta[content]`, `html[manifest]`, doctype `system`, button `formaction`, blockquote `cite`, map area `ping`, `input[type=image]`. There is also an HTMX-aware parser `bodyHtmxAttrParser` (`pkg/engine/parser/parser.go:634`) that emits `GET/POST/PUT/PATCH` requests for `hx-get|hx-post|hx-put|hx-patch` attributes.

Header parsers handle `Content-Location`, `Link` (RFC 5988 via `utils.ParseLinkTag`), `Location` (added when redirects enabled), and `Refresh` (`pkg/engine/parser/parser.go:122-165`).

Optional parsers are appended at runtime in `InitWithOptions` (`pkg/engine/parser/parser_generic.go:22`): form auto-fill (`bodyFormTagParser` builds a synthetic POST/GET body via `utils.FormFillSuggestions`), regex JS extraction (`scriptContentRegexParser`, `scriptJSFileRegexParser`, `bodyScrapeEndpointsParser`), and jsluice (`scriptContentJsluiceParser` / `scriptJSFileJsluiceParser` using `github.com/Mzack9999/jsluice`, `pkg/utils/jsluice.go:36`). The jsluice parsers skip a long allowlist of common JS libraries via `IsPathCommonJSLibraryFile` (`pkg/utils/jsluice.go:18`) — a single regex (`pkg/utils/jsluice.go:13`) covering jQuery, Bootstrap, React, Vue, ad networks, etc.

The hybrid engine *additionally* uses CDP `Fetch.requestPaused` events as a parser source (see §4): the synthetic `http.Response` flows back through `c.Options.Parser.ParseResponse(resp)` (`pkg/engine/hybrid/crawl.go:184`), so HTML, JS-discovered and XHR endpoints all funnel through the same parser stack.

Custom-field regex extraction (`customFieldRegexParser`, `pkg/engine/parser/parser.go:718`) runs user-defined patterns from `field-config.yaml` against `body`, `header`, or whole `response` and emits a synthetic request carrying `CustomFields`.

## 7. Output

`pkg/output/result.go:10` defines the canonical `Result{Timestamp, *Request, *Response, Error}`. Three formatters live behind `Writer.Write` (`pkg/output/output.go:236`): `formatTemplate` (fasttemplate `{{...}}`), `formatJSON` (jsoniter, `pkg/output/format_json.go:9` — uses `structs.FilterStructToMap` so `--exclude-output-fields` removes keys at the request/response level), and `formatScreen` (aurora-coloured). `--omit-raw` and `--omit-body` zero those fields before formatting (`pkg/output/output.go:224`).

Filtering happens inside `Write`: extension validator (`extensions.Validator.ValidatePath`), `matchRegex`/`filterRegex`, DSL `match-condition`/`filter-condition` evaluated via `projectdiscovery/dsl` (`pkg/output/output.go:392`), and `filter-page-type` against the dit-classifier's `PageType` (`pkg/output/output.go:192`).

Field scope for `-f`/`-sf` is built-in field names (`FieldNames` at `pkg/output/fields.go:18`: `url, path, fqdn, rdn, rurl, qurl, qpath, file, ufile, key, value, kv, dir, udir`) plus user-defined custom fields. With `-sf` enabled, results are appended to per-host files `<scheme>_<host>_<field>.txt` under `katana_field/` (`pkg/output/fields.go:86`), which `main()` post-processes by deduplicating lines (`cmd/katana/main.go:120`).

`--store-response` mirrors raw HTTP request/response pairs into `katana_response/` with a per-target index file; `--no-clobber` increments the directory suffix instead of removing it (`pkg/output/output.go:131, 307`).

## 8. Concurrency

Three tiers:

1. **Across targets**: `sizedwaitgroup.New(options.Parallelism)` in `internal/runner/executer.go:32` (default 10).
2. **Within a target (standard)**: `sizedwaitgroup.New(s.Options.Options.Concurrency)` in `Shared.Do` (`pkg/engine/common/base.go:406`, default 10). Hybrid bypasses this with its own sequential `Do` (`pkg/engine/hybrid/hybrid.go:150`).
3. **Rate limiting**: in `types.NewCrawlerOptions` (`pkg/types/crawler_options.go:147`), `--host-rate-limit` / `-hrlm` builds a `ratelimit.NewAutoLimiter` keyed by hostname; otherwise `--rate-limit` / `-rlm` builds a global `ratelimit.New`. Workers call `HostRateLimit.Take(host)` or `RateLimit.Take()` *inside* the per-request goroutine, raced against the session context so shutdown isn't blocked by a pending limiter tick (`pkg/engine/common/base.go:454-467`, same pattern at `pkg/engine/hybrid/hybrid.go:195-208`).

Adaptive backoff: `Shared.RecordThrottle` increments a per-host counter on 429/503, `ApplyBackoff` sleeps `min(backoffBase·2^(n-1), 30s) + jitter` before the next request, and `RecordSuccess` decrements (`pkg/engine/common/base.go:262-289`). The state lives in an LRU bounded at 10 000 hosts (`pkg/engine/common/base.go:46`).

Deduplication uses `hmap/store/hybrid` (memory + disk spillover) for both unique-URL and unique-content (MD5) sets (`pkg/utils/filters/simple.go:24, 47`). Cycle detection guards against URLs that exceed `MaxChromeURLLength` (2 MiB) or contain a repeating sequence ≥10 chars repeated ≥10 times (`pkg/utils/filters/simple.go:65`). The queue itself (`pkg/utils/queue/queue.go:20`) is a single-mutex wrapper around either a stack (DFS) or a priority queue (BFS, with depth as priority), selected by `--strategy`.

## 9. What's genuinely novel at the code level

The architectural fingerprint is the **trifurcated engine sharing a single `common.Shared`**: one `Crawl(URL) error` contract, one `Enqueue → Parser.ParseResponse → Enqueue` loop, but two opposing execution models — `net/http`+`goquery` for speed, go-rod with Fetch-domain hijacking for fidelity — and a third pure-headless engine being grown alongside (`pkg/engine/headless/`, ~3 000 LOC with its own browser pool, captcha solver registry, debugger UI on :8089). The hybrid engine's trick of routing CDP `Fetch.requestPaused` events back through the *same* HTML/JS parser stack used for static crawling (`pkg/engine/hybrid/crawl.go:184`) means XHR responses, sub-resources and navigations all reach the queue via one code path. "Modern Go crawler" in practice means: fastdialer + JA3 impersonation as the default transport (`pkg/engine/common/http.go:30`), `hmap` hybrid-store dedup that spills to disk for long crawls, an LRU-bounded per-host adaptive backoff (`pkg/engine/common/base.go:46`), pluggable BFS/DFS queue with depth-as-priority (`pkg/utils/queue/queue.go`), publicsuffix-driven scope (`pkg/utils/scope/scope.go:153`), and Shadow-DOM piercing via `DOM.getDocument{Pierce:true,Depth:-1}` (`pkg/engine/hybrid/crawl.go:346`) — none individually exotic, but the combination, plus the engine-swap design, is the differentiator from older Go crawlers like hakrawler/gospider.
