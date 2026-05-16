# Vespasian — code-level analysis

Vespasian is a Go CLI that fabricates API specifications (OpenAPI 3.0, GraphQL SDL, WSDL) from wire traffic it either captures itself or ingests from third-party tools. The Apache-2.0 codebase is roughly 100 Go files (~30 KLOC) under `sources/appsec/vespasian/`.

## 1. Architecture overview

The pipeline is split into two cleanly separable stages mediated by a JSON intermediate (`capture.json`):

1. **Capture** — produce a `[]crawl.ObservedRequest`. Either `CrawlCmd` (live headless crawl) or `ImportCmd` (Burp / HAR / mitmproxy) writes the array as JSON via `crawl.WriteCapture` (`pkg/crawl/capture.go:26`).
2. **Generate** — `GenerateCmd` reads the array back via `crawl.ReadCapture` (`pkg/crawl/capture.go:33`) and runs classify → probe → spec render.

A `ScanCmd` glues both stages in-process (`cmd/vespasian/main.go:562`); the on-disk schema (`pkg/crawl/types.go:18` — `ObservedRequest{Method, URL, Headers, QueryParams, Body, Response, Source, Tag, Attribute, PageURL}`) is the single contract that decouples them. The entry point is `main()` at `cmd/vespasian/main.go:670`, which uses Kong for subcommand dispatch.

`generateSpec` (`cmd/vespasian/main.go:695`) is the canonical pipeline: pick classifier → `classify.RunClassifiers` → optional `classify.Deduplicate` → choose probe strategies by API type → `generate.Get(apiType).Generate(...)`.

## 2. Module / package layout

```
cmd/vespasian/             CLI + Kong commands + signal/browser lifecycle
pkg/crawl/                 Live headless crawler (go-rod + Katana), capture I/O
pkg/importer/              Burp / HAR / mitmproxy adapters, format registry
pkg/classify/              Heuristic classifiers (REST, GraphQL, WSDL) + dedup
pkg/probe/                 Active probes: OPTIONS, JSON schema, GraphQL introspect, WSDL fetch
pkg/generate/              Spec generator registry
pkg/generate/rest/         OpenAPI 3.0 (kin-openapi + yaml.v3)
pkg/generate/graphql/      SDL via gqlparser (introspection-first, traffic fallback)
pkg/generate/wsdl/         WSDL XML render + parse-passthrough
internal/tnetenc/          tnetstring decoder for mitmproxy native flow dump
```

The two pluggable registries are intentional architectural seams: `pkg/importer/registry.go:24` (`burp/har/mitmproxy → TrafficImporter`) and `pkg/generate/registry.go:26` (`rest/wsdl/graphql → SpecGenerator`).

## 3. Capture pipeline

Every ingest path converges on a `[]crawl.ObservedRequest`. The four sources are:

**Burp XML** — `pkg/importer/burp.go:69`. Stream-parses the `<items>/<item>` tree with `encoding/xml`, base64-decodes `<request>`/`<response>` per the `base64="true"` attribute (`pkg/importer/burp.go:167`), then hand-parses the raw HTTP wire bytes via `splitHTTPMessage` (`pkg/importer/burp.go:180`) — splitting on `\r\n\r\n` or `\n\n`, validating the method against an explicit allowlist (`pkg/importer/burp.go:37`), and recovering the status code from the response start-line.

**HAR 1.2** — `pkg/importer/har.go:68`. Direct `json.Decoder` deserialization through `harLog → harEntry`; header arrays are folded into a `map[string]string` via `convertHeaders` (`pkg/importer/har.go:122`).

**mitmproxy** — `pkg/importer/mitmproxy.go:73` performs format autodetection by peeking the first non-whitespace byte (`peekFirstNonWhitespace`, line 440): `[`/`{` selects the streaming JSON path, an ASCII digit selects the native tnetstring path (`importNative`, line 195). The native path iterates flow dicts via `decodeTnetstringStream` (the in-house `internal/tnetenc` decoder), skips non-`http` records (`pkg/importer/mitmproxy.go:232`), and translates each via `flowFromNativeState` (line 262). A 500 K-flow cap (`pkg/importer/mitmproxy.go:191`) bounds adversarial inputs; `validateHost` (line 494) rejects credential-smuggling hostnames.

**Live crawl** — `pkg/crawl/crawler.go:84`. Splits into `crawlHeadless` (`pkg/crawl/crawler.go:128`, the default path, using go-rod directly) and `crawlStandard` (line 202, Katana's HTTP engine).

The per-source unified-representation pattern is the same shape in every parser: parse → build URL → validate method/scheme → convert headers to map → assign `Source: "import:<name>"` (or `"katana"` for crawled requests, `pkg/crawl/crawler.go:334`) → return `crawl.ObservedRequest`. The `Source` string is preserved end-to-end and is the only field that lets downstream consumers tell which adapter produced the request.

## 4. katana integration

Imported in `pkg/crawl/crawler.go:27-29` (`engine/standard`, `output`, `types`). Used only by `crawlStandard` (`pkg/crawl/crawler.go:202`):

```go
katanaOpts := &types.Options{
    MaxDepth:               c.opts.Depth,
    FieldScope:             MapScope(c.opts.Scope),
    Headless:               false,
    Strategy:               "depth-first",
    ScrapeJSResponses:      true,
    ScrapeJSLuiceResponses: true,   // jsluice integration for SPA URL extraction
    XhrExtraction:          true,
    OnResult: func(result output.Result) { ... },
}
```
(`pkg/crawl/crawler.go:210-242`)

For headless SPA crawling, Vespasian does *not* use Katana's hybrid engine. Instead it launches its own Chrome via go-rod's `launcher` (`pkg/crawl/browser.go:60`, `BrowserManager`), then either (a) hands the CDP WebSocket URL to Katana via `katanaOpts.ChromeWSUrl = browserMgr.wsURL()` (`pkg/crawl/crawler.go:245`) for the legacy `crawlStandard` path, or (b) drives Chrome directly through `newRodEngine` (`pkg/crawl/engine.go:125`) for the default `crawlHeadless` path. Per the comment at `pkg/crawl/crawler.go:200`, Katana is documented as scheduled for removal — go-rod direct capture (`pkg/crawl/network.go:48`, `pageNetworkCapture`) is the current default because it gives passive CDP `Network.requestWillBeSent`/`responseReceived` hooks and concurrent-tab parallelism that Katana's serial engine cannot match. Result-to-`ObservedRequest` translation lives in `MapResult` (`pkg/crawl/crawler.go:331`).

## 5. Classifier / endpoint canonicalizer

Classification (`pkg/classify/classifier.go:41`, `RunClassifiers`) runs each request through every classifier, keeps the highest-confidence match above a configurable threshold, and emits a `ClassifiedRequest` (`pkg/classify/types.go:22`) that embeds the original observation plus `IsAPI`, `Confidence`, `Reason`, `APIType`. Three classifiers exist: `RESTClassifier` (`pkg/classify/rest.go:55`), `GraphQLClassifier` (`pkg/classify/graphql.go:41`), `WSDLClassifier` (`pkg/classify/wsdl.go:26`). Each is a small ordered ruleset over path/headers/body — REST uses five rules (static exclusion → content-type → path-segment boost → method signal → JSON body shape; `pkg/classify/rest.go:76-162`), WSDL takes the max across SOAPAction/envelope/`?wsdl`/content-type and has a negative signal that demotes RSS/Atom feeds (`pkg/classify/wsdl.go:115-122`).

Canonicalization happens in two places:

1. **Deduplication key** — `classify.Deduplicate` (`pkg/classify/classifier.go:86`) uses `METHOD:URL.Path` as the dedup key, deliberately strips query string and host, and merges `QueryParams` from collapsed observations (line 122-132). For SOAP it appends the `SOAPAction` header to the key (line 113) so distinct operations on the same path stay distinct.
2. **Path-parameter detection** — `NormalizePathWithNames` (`pkg/generate/rest/normalize.go:64`) walks path segments, matches each against `uuidRegex` (8-4-4-4-12 hex, line 25) or `numericRegex` (line 27), and replaces with a *context-aware* placeholder: it walks backward to the preceding non-empty, non-parameterized segment and runs `paramNameFromContext` → `singularize` → `+ "Id"` so `/users/42` becomes `/users/{userId}` and `/categories/123` becomes `/categories/{categoryId}` (line 128 + the naive singularizer at line 139). Collisions are disambiguated with numeric suffixes (line 92-101).

Query-parameter normalization is in `MapResult` (`pkg/crawl/crawler.go:357-366`): multi-value query keys collapse to first-value-only — explicitly noted because "the classifier needs parameter names, not all values".

## 6. Spec generation

Three independent renderers behind the `SpecGenerator` interface (`pkg/generate/generator.go:22`), routed by `generate.Get` (`pkg/generate/registry.go:26`):

- **OpenAPI** — `pkg/generate/rest/openapi.go:316` (`OpenAPIGenerator.Generate`). Groups by `endpointKey{normalizedPath, method}` (`groupEndpoints`, line 105), builds operations via `buildOperation` (line 126) which merges request bodies and responses across all observations for the group, extracts servers from observed hosts (`extractServers`, line 76), then post-processes inline schemas into `components/schemas` via `extractComponents` (line 463). Component reuse is driven by `schemaFingerprint` (line 445), a sorted `prop:type` digest. Validation round-trips through `openapi3.NewLoader().LoadFromData` (line 390-393) before emit; YAML output reuses the validation buffer (line 407). Resource naming derives from `resourceNameFromPath` + `singularize` (line 430) so a group on `/api/v2/tickets/{ticketId}` produces components named `Ticket`, `CreateTicketRequest`, `TicketResponse` (lines 487-508 + 550-560).
- **GraphQL SDL** — `pkg/generate/graphql/sdl.go:51` (`Generator.Generate`) tries `generateFromIntrospection` first if any endpoint carries a `GraphQLSchema` field populated by the probe (line 57-61), otherwise falls back to `inferSDL` (`pkg/generate/graphql/infer.go:60`). `typeRefToSDL` (`pkg/generate/graphql/sdl.go:240`) handles the recursive `NON_NULL`/`LIST`/named-type unwrap. The inference path parses observed query strings with `vektah/gqlparser` (`pkg/generate/graphql/infer.go:29`) and synthesizes types from response shapes.
- **WSDL** — `pkg/generate/wsdl/generator.go:40`. Same two-phase pattern: if any endpoint has a `WSDLDocument` from probing (or a response body that round-trips through `ParseWSDL`), emit that verbatim — otherwise build a synthetic definitions tree via `InferWSDL` (`pkg/generate/wsdl/infer.go:29`) by extracting operations from `SOAPAction` headers and/or the SOAP envelope's first child element (`extractOperation`, line 139), then `xml.MarshalIndent` it with an XML declaration prefix (`pkg/generate/wsdl/generator.go:72-73`).

## 7. Type inference

`InferSchema` (`pkg/generate/rest/schema.go:32`) is the JSON-to-OpenAPI-3.0 heuristic. It `json.Unmarshal`s into `interface{}` and walks `inferSchemaFromValue` (line 50) recursively with a depth bound of 20 (`maxSchemaDepth`, line 28) and a 10 MB body bound (line 26). The Go type switch (line 69) maps `string → "string"`, `float64 → "integer"` if the value is `Trunc(v)==v` and inside int64 range else `"number"` (line 79), `bool → "boolean"`, arrays infer item schema from the first element (line 102-105), objects recurse on each property. `null` becomes `Nullable: true` rather than emitting a type because OpenAPI 3.0 has no `"null"` type (line 60-67).

There is no enum detection in either inference path I located (no histogram of repeated string values is built in `pkg/generate/rest/schema.go`), and "required vs optional" is *not* derived from per-property frequency in REST — `buildOperation` (`pkg/generate/rest/openapi.go:126`) only marks query-parameter required when `info.count == endpointsWithParams` (i.e. every observation has it) (line 167). Request-body property presence is unioned across observations (lines 219-226), but no `required` set is computed. GraphQL inference reads observed JSON-scalar enum values into a separate map (`observedEnumValues`, `pkg/generate/graphql/infer.go:65`) — the only place enum-detection actually happens.

Schema merging across multiple observations of the same endpoint group happens twice: request-body union (`pkg/generate/rest/openapi.go:202-227`) and response-body union per status code (lines 242-269). Both add missing properties to the merged schema rather than reconciling type conflicts.

## 8. Authentication detection

**Not implemented.** Grepping for `securitySchemes`, `SecurityScheme`, `apiKey`, `Bearer`, and `Authorization` in `pkg/generate/` and `pkg/classify/` (non-test) returns zero matches. `OpenAPIGenerator.Generate` (`pkg/generate/rest/openapi.go:316`) constructs the document with `Info` + `Paths` + `Servers` + `Components.Schemas` only; it never populates `Components.SecuritySchemes` or any operation's `Security` field. Headers seen in `ObservedRequest.Headers` flow into the spec only as part of `Headers` JSON; they are not classified or surfaced as authentication scheme metadata. The capture pipeline does *use* an injected cookie/session for crawling (`ApplyCookieHeader`, `pkg/crawl/cookies.go`, called from `pkg/crawl/crawler.go:149`) — but observed inbound `Authorization` / `Cookie` / `X-API-Key` headers are not reflected back into the generated spec as `securitySchemes`. **This is a notable gap relative to what the README implies.**

## 9. What's genuinely novel at the code level

The "third path" framing — discovering APIs by observing real wire traffic rather than by static binary analysis or well-known route fuzzing — translates concretely into two design choices:

1. **A unifying observation type (`crawl.ObservedRequest`, `pkg/crawl/types.go:18`) that is provenance-agnostic.** A Burp item, a HAR entry, a mitmproxy native flow, and a live-Chrome CDP event all collapse to the same struct, tagged only by `Source`. Every downstream stage (classify, probe, generate) operates on this single type, so adding a fifth ingest path requires only a new `TrafficImporter` registration — no changes to classifiers or generators. The mitmproxy native-format support specifically (`pkg/importer/mitmproxy.go:195` plus the in-house `internal/tnetenc` decoder) is unusual: most OSS tools require users to pre-convert `.mitm` files to HAR.

2. **Two-phase generators that prefer ground-truth schema documents to inference.** `wsdl.Generator.Generate` (`pkg/generate/wsdl/generator.go:46-58`) and `graphql.Generator.Generate` (`pkg/generate/graphql/sdl.go:57-61`) both check first for a probe-fetched schema artifact attached to the `ClassifiedRequest` (`WSDLDocument`, `GraphQLSchema`) and emit that verbatim or via deterministic SDL render; only if no authoritative schema was recovered do they fall back to traffic-shape inference. The OpenAPI path lacks an equivalent because there is no analogous well-known authoritative document — but the active `?wsdl` synthetic-request injection at `cmd/vespasian/main.go:611-630` shows the same "probe for an authoritative document, fall back to inference" pattern stitched into the scan orchestrator itself.
