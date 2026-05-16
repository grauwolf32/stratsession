# httpx — code-level analysis

ProjectDiscovery's `httpx` is a Go HTTP probe and fingerprinting toolkit. The thin `main` only parses flags, sets up optional cloud/db sinks and signals, then delegates to `runner.Runner`. All scan logic lives in the `runner` and `common/httpx` packages.

## 1. Architecture overview

`cmd/httpx/httpx.go:20` is a 200-line `main()` that calls `runner.ParseOptions()`, wires optional asset upload (`cmd/httpx/httpx.go:105`) and result DB sinks (`cmd/httpx/httpx.go:158`), constructs the runner with `runner.New(options)` (`cmd/httpx/httpx.go:71`), installs a two-stage SIGINT handler (first `Interrupt()`, second `os.Exit(1)`) at `cmd/httpx/httpx.go:77`, then calls `RunEnumeration()` (`cmd/httpx/httpx.go:90`).

The `Runner` struct (`runner/runner.go:82`) owns the long-lived collaborators: `hp *httpx.HTTPX` (the HTTP client wrapper), `wappalyzer *wappalyzer.Wappalyze`, `cpeDetector`, `wpDetector`, `ratelimit.Limiter`, a `hybrid.HybridMap` of deduped targets, a `gcache` for host-error tracking, `simHashes` for near-duplicate suppression, and the optional `browser` / `ditClassifier`.

The per-target pipeline has three layers:

- `RunEnumeration` (`runner/runner.go:943`) — the main loop. Allocates an `AdaptiveWaitGroup` (`runner/runner.go:1509`), iterates input either by streaming (`r.hm.Scan` at `runner/runner.go:1569`) or `streamInput()` (`runner/runner.go:711`), and calls `processItem` which dispatches to `r.process(...)`.
- `process` (`runner/runner.go:1671`) — the per-target fan-out: expands the target into ports/methods/protocols and recursively re-feeds discovered TLS SAN/CN and CSP domains back through `process` (`runner/runner.go:1701, 1715`).
- `analyze` (`runner/runner.go:1829`) — the actual probe of one (URL, method, protocol) tuple, returning a `Result`.

`Process(URL)` (capital P) is the exported entry (`runner/runner.go:1667`) which just forwards to the unexported `process`.

## 2. Module / package layout

- `cmd/httpx/` — entry point only (`cmd/httpx/httpx.go`).
- `runner/` — CLI flag parsing (`runner/options.go`, 955 lines), orchestration (`runner/runner.go`, 3 071 lines), `Result` struct + DSL/CSV/JSON serializers (`runner/types.go`), CPE detector (`runner/cpe.go`), WordPress detector (`runner/wordpress.go`), headless screenshot driver (`runner/headless.go`), markdown writer (`runner/md_output.go`), API server (`runner/apiendpoint.go`), ports-optimization heuristic (`runner/ports_optimization.go`), resume.cfg helpers, and health-check.
- `common/httpx/` — the request-level library: `httpx.go` (`HTTPX` struct + `Do`), `cdn.go`, `tls.go` (TLS-grab via `tlsx/pkg/tlsx/clients`), `csp.go`, `domains.go` (body FQDN scraping), `title.go`, `encodings.go`, `virtualhost.go`, `pipeline.go`, `http2.go`, `proto.go` (the `HTTP/HTTPS/HTTPandHTTPS/HTTPorHTTPS` constants), `response.go`, `filter.go`.
- `common/` sub-packages: `customports/customport.go` (nmap-style port-list parser), `customheader/`, `customlist/`, `customextract/`, `hashes/` (md5/sha/mmh3/simhash) plus `hashes/jarm`, `httputilz/`, `stringz/` (favicon mmh3, base64 utils), `fileutil/`, `authprovider/`, `inputformats/` (burp/openapi/swagger raw parsers).
- `static/` — the embedded HTML summary template (`static/static.go`, `static/html-summary.html`) used by `-ss` / `-svrc`.
- `internal/` — `db/` (optional MongoDB/Postgres/MySQL sink), `pdcp/` (PD Cloud upload), `testutils/`.

Subpackages worth highlighting: `common/httpx` is reusable as a library; `runner/cpe.go` ships an embedded fingerprint DB via the `projectdiscovery/awesome-search-queries` module (`runner/cpe.go:8`).

## 3. Probe pipeline

The central per-probe function is `(*Runner).analyze` (`runner/runner.go:1829`). Linearised:

1. **Scheme resolution.** If protocol is `HTTPorHTTPS`/`HTTPandHTTPS`, `determineMostLikelySchemeOrder` picks HTTP first for common HTTP ports and any port > 1024, otherwise HTTPS (`runner/ports_optimization.go:17`).
2. **URL parse + host-error cache.** Skips host:port that previously exceeded `HostMaxErrors` (`runner/runner.go:1846`, gcache ARC at `runner/runner.go:427`).
3. **CDN-skip / exclude check.** `r.skip(URL, target, origInput)` (`runner/runner.go:1854`, impl at `runner/runner.go:2712` and `runner/runner.go:2979`).
4. **Request build.** `hp.NewRequestWithContext` (`runner/runner.go:1885`); a custom IP for the dialer is injected via `fastdialer.IP` context key (`runner/runner.go:1881`) — this is what lets `-probe-all-ips` send Host=name but dial=ip.
5. **Custom headers + per-URL auth.** `hp.SetCustomHeaders` (`runner/runner.go:1903`); `authProvider.LookupURLX(URL)` then `strategy.ApplyOnRR(req)` (`runner/runner.go:1906-1912`).
6. **Rate-limit gate.** `r.ratelimiter.Take()` (`runner/runner.go:1923`).
7. **Send.** `hp.Do(req, httpx.UnsafeOptions{URIPath: reqURI})` (`runner/runner.go:1929`). Inside `HTTPX.Do` (`common/httpx/httpx.go:220`): reads body (size-capped via `MaxResponseBodySizeToRead`), dumps raw headers via `pdhttputil.DumpResponseHeadersAndRaw`, transparently retries with `Accept-Encoding: identity` on gzip errors (`common/httpx/httpx.go:260`), grabs TLS data (`common/httpx/httpx.go:329`), CSP + body FQDNs if `ExtractFqdn` is set (`common/httpx/httpx.go:338`), builds the redirect chain via `pdhttputil.GetChain` (`common/httpx/httpx.go:345`).
8. **Auto-fallback.** On error with `HTTPorHTTPS`, switches scheme and port 80↔443 once via a `goto retry` (`runner/runner.go:2012`).
9. **Output enrichment** appended to a `strings.Builder` in this order: status code, location, method, content-length, content-type, title (`runner/runner.go:2122` via `httpx.ExtractTitle`), body preview, server header, optional `IsVirtualHost` second request (`runner/runner.go:2196`), `SupportPipeline` (`runner/runner.go:2212`), `SupportHTTP2` (`runner/runner.go:2225`), IP from `Dialer.GetDialedIP` (`runner/runner.go:2242`), ASN, DNS (A/AAAA/CNAME), CDN, tech detect, regex extracts, favicon, hashes, JARM, words/lines, optional screenshot.
10. **Result assembly** at `runner/runner.go:2638`.

The same `analyze` runs against custom-port URLs from a separate goroutine fan-out in `process` (`runner/runner.go:1723`).

## 4. Tech detection

httpx uses **`github.com/projectdiscovery/wappalyzergo`** — PD's pure-Go Wappalyzer port (imported at `runner/runner.go:78`, `runner/options.go:36`). The signature DB is embedded in the wappalyzergo module (so there is no external `technologies.json`); `wappalyzer.New()` at `runner/runner.go:156` loads it, while `-cff/--custom-fingerprint-file` switches to `wappalyzer.NewFromFile(...)` (`runner/runner.go:154`).

The actual match call lives in `analyze`:

```go
matches := r.wappalyzer.FingerprintWithInfo(resp.Headers, resp.Data)   // runner/runner.go:2315
```

returning `map[string]wappalyzer.AppInfo` (categories, CPE, version). A second pass runs against the rendered headless body when `-ss` is on (`runner/runner.go:2568`). Tech-detect is implicitly enabled whenever JSON/CSV/asset-upload is on (`runner/runner.go:343`).

A second product-level detector, `runner/cpe.go:35` `NewCPEDetector`, loads PD's `awesome-search-queries` JSON into three pattern maps (title/body/favicon-mmh3) and is invoked at `runner/runner.go:2599` as `r.cpeDetector.Detect(title, body, faviconMMH3)`. WordPress plugin/theme enumeration lives in `runner/wordpress.go` and is called at `runner/runner.go:2615`.

## 5. CDN detection

The `cdncheck` library is wired into `common/httpx/httpx.go:17`. The client is lazily constructed at `common/httpx/httpx.go:212`:

```go
if options.CdnCheck != "false" || options.ExcludeCdn {
    httpx.cdn = cdncheck.New()
}
```

The wrapper `(*HTTPX).CdnCheck(ip)` (`common/httpx/cdn.go:9`) calls `cdn.Check(net.ParseIP(ip))` and explicitly down-grades `itemType == "cloud"` to a non-CDN result so cloud-hosted assets are still scanned (`common/httpx/cdn.go:17`). It is invoked from `analyze` at `runner/runner.go:2303`, producing `isCDN`, `cdnName`, `cdnType` that feed into the `Result` (`runner/runner.go:2673`). Port-level CDN skipping happens earlier in `(*Runner).skipCDNPort` (`runner/runner.go:2979`).

## 6. Custom-port scanning

Ports come from `-p/--ports` parsed by `customport.CustomPorts.Set` (`common/customports/customport.go:33`). The syntax is nmap-like with optional scheme prefix:

```
[http:|https:|http+https:]N[,...]   and N can be a range a-b
```

(`common/customports/customport.go:34`). Parsed entries land in the package-global `Ports map[int]string` (`common/customports/customport.go:22`), where the value is the wanted protocol per port. Conflicting schemes for the same port are collapsed to `HTTPandHTTPS` (`common/customports/customport.go:63`).

`(*Runner).process` then iterates `customport.Ports` (`runner/runner.go:1723`), rewrites the URL via `urlx.UpdatePort(fmt.Sprint(port))` (`runner/runner.go:1745`) and launches one goroutine per (port, protocol, method) tuple, all sharing the same waitgroup. `-nfs/--no-fallback-scheme` forces the input scheme over the per-port scheme (`runner/runner.go:1728`).

## 7. Output writers

Field selection is driven by per-flag `ScanOptions` booleans (e.g. `OutputStatusCode`, `OutputServerHeader`, `TechDetect`) that the runner consults inside `analyze`; everything is appended to the same `strings.Builder` used for plain CLI output (e.g. `runner/runner.go:2050` status, `runner/runner.go:2160` server, `runner/runner.go:2587` tech).

Three structured writers are selected in the output loop at `runner/runner.go:990`:

- **JSONL** — `Result.JSON(scanopts)` at `runner/runner.go:2918` does `json.Marshal(r)` with body trimming. Called at `runner/runner.go:1407`.
- **CSV** — `Result.CSVRow` (`runner/runner.go:2943`) and `Result.CSVHeader` (`runner/runner.go:2931`) use `gocarina/gocsv` reflection over the `csv:"..."` struct tags on `Result` (`runner/types.go:36`). Each cell is rewritten to a leading `'` if it starts with `= + - @` to prevent CSV injection (`runner/runner.go:2961`). UTF-8 BOM is written when `-csvo utf-8` is set (`runner/runner.go:1068`).
- **Markdown** — `runner/md_output.go` writes a markdown table via the `md:"..."` tags.
- **Plain text** is just `result.str` (the `strings.Builder` output from `analyze`).

`-oa/--output-all` causes all three sink files to be opened side by side with `.json/.csv/.md` suffixes (`runner/runner.go:1021-1061`).

## 8. Probe options

- **`-follow-redirects` / `-fhr` / `-rhsts`.** Configured in the `retryablehttp.Client` constructor at `common/httpx/httpx.go:88-139`. Three custom `CheckRedirect` closures: never-follow, follow-up-to-`MaxRedirects`, and same-host-only. `RespectHSTS` calls `handleHSTS` to rewrite `req.URL.Scheme = "https"` (`common/httpx/httpx.go:80`).
- **`-tls-grab`.** Branch in `Do` at `common/httpx/httpx.go:329`. Implementation at `common/httpx/tls.go:25` (`TLSGrab`) builds a `tlsx/pkg/tlsx/clients.Response` from `r.TLS.PeerCertificates[0]`; `-ztls` switches to `ZTLSGrab`. Output goes into `Result.TLSData`, and SubjectAN/SubjectCN are re-fed into `process` when `-tls-probe` is on (`runner/runner.go:1697`).
- **`-favicon` (mmh3).** Handled in `(*Runner).HandleFaviconHash` (`runner/runner.go:2742`). Parses `<link rel="...icon...">` and `<base href>` from the HTML (`runner/runner.go:2870` `extractPotentialFavIconsURLs` using `goquery`), falls back to `/favicon.ico` (`runner/runner.go:2757`), supports `data:` URLs (`runner/runner.go:2796`), and hashes via `stringz.FaviconHash` (`common/stringz/stringz.go:143`) — which does Shodan-style base64-encode-with-`\n`-every-76-chars then `murmur3.New32WithSeed(0)` (`common/stringz/stringz.go:128`).
- **`-jarm`.** `jarm.Jarm(r.hp.Dialer, fullURL, r.options.Timeout)` at `runner/runner.go:2432`; implementation lives in `common/hashes/jarm/`.
- **`-asn`.** Uses `asnmap.DefaultClient.GetData(ip)` and `asnmap.GetCIDR(results)` at `runner/runner.go:2251-2263` to fill `AsnResponse{AsNumber, AsName, AsCountry, AsRange}` (`runner/types.go:23`).

## 9. Concurrency and rate limit

Threading is a `syncutil.AdaptiveWaitGroup` allocated at `runner/runner.go:1509` with size `options.Threads` (default 50, `runner/options.go:41`). `process` dynamically resizes it via `wg.Resize(ctx, r.options.Threads)` when the option changes (`runner/runner.go:1673-1677`), which is what makes the runtime `-stats` knob meaningful.

Rate limit is a `projectdiscovery/ratelimit.Limiter` chosen at `runner/runner.go:418`:

```go
if RateLimitMinute > 0     -> ratelimit.New(ctx, RateLimitMinute, time.Minute)
else if RateLimit > 0       -> ratelimit.New(ctx, RateLimit,       time.Second)   // default 150/s
else                        -> ratelimit.NewUnlimited(ctx)
```

`Take()` is called before every primary request (`runner/runner.go:1923`) and before each auxiliary probe (vhost `2195`, pipeline `2211`, http2 `2224`). There is no per-host token bucket — back-pressure on misbehaving hosts comes from the `HostErrorsCache` (`runner/runner.go:1846`), an ARC-evicting `gcache` keyed by `host:port` that short-circuits after `-maxhr` (default 30) failures. `-delay` adds a `time.Sleep(r.options.Delay)` before each `wg.Add()` (`runner/runner.go:1690, 1738`).

The fastdialer (`common/httpx/httpx.go:66`) handles DNS caching and the `WithDialerHistory` mode that lets `GetDialedIP` return the actual connected IP per host (`runner/runner.go:2242`).

## 10. Genuinely novel at the code level

1. **Recursive scope expansion from probe artefacts.** `process` feeds TLS Subject Alternative Names and CSP `connect-src` domains back into itself as new targets (`runner/runner.go:1697-1716`), turning a single seed into a discovery walk without an external resolver — uncommon in HTTP probes, which usually treat the target list as fixed.
2. **Simhash-based response de-duplication and DIT page-type classifier.** `(*Runner).duplicate` (`runner/runner.go:640`) builds a simhash of the raw response and skips results within Hamming distance 3, keyed per IP — this is what `-fd` actually does. Combined with `happyhackingspace/dit` (`runner/runner.go:39`, `runner/runner.go:435`) the runner can drop "login/captcha/parked" pages by class rather than by status code.
3. **Shodan-compatible favicon mmh3 implemented inline.** `stringz.murmurhash` (`common/stringz/stringz.go:128`) reproduces Shodan's exact "base64 with `\n` every 76 chars, then mmh3-32 seed 0" recipe; this is the reason `-favicon` hashes from httpx can be pivoted directly via Shodan/Censys queries without re-encoding.
