# Coraza — code-level analysis

Submodule rooted at `sources/appsec/coraza/` (module `github.com/corazawaf/coraza/v3`, Go, Apache-2.0).

## 1. Architecture overview

`coraza.NewWAF(WAFConfig)` is the only constructor for production callers; it instantiates an internal `corazawaf.WAF`, spins up a `seclang.NewParser(waf)`, then ingests `WithDirectives`/`WithDirectivesFromFile`/`WithRootFS` entries before returning a `wafWrapper` that satisfies the `WAF` interface (`waf.go:31` and `waf.go:146-178`). The interface is deliberately narrow: just `NewTransaction()` / `NewTransactionWithID()` returning a `types.Transaction` (`waf.go:24-28`).

A `Transaction`'s public lifecycle is a strict sequence enforced by `lastPhase` guards inside `internal/corazawaf/transaction.go`:

```
ProcessConnection  -> ProcessURI  -> ProcessRequestHeaders   (phase 1)
                                  -> ProcessRequestBody      (phase 2)
                                  -> ProcessResponseHeaders  (phase 3)
                                  -> ProcessResponseBody     (phase 4)
                                  -> ProcessLogging          (phase 5, always runs)
```

`ProcessConnection` only sets `remoteAddr/remotePort/serverAddr/serverPort` collection scalars — no rule eval (`transaction.go:742`). `ProcessURI` parses the URI with `net/url`, sets `requestURI/requestFilename/requestBasename/queryString`, and folds the query string into `ARGS_GET` via `ExtractGetArguments` (`transaction.go:819-867`). Each subsequent `Process*` delegates the matching to `tx.WAF.Rules.Eval(<phase>, tx)` after guarding against re-entry and pre-existing interruptions. `ProcessLogging` additionally drives the audit-log writer subject to `AuditEngineRelevantOnly` filtering (`transaction.go:1393-1435`).

Interruption is just a non-nil `*types.Interruption` stored on the transaction; the rule loop checks `tx.IsInterrupted()` between rules and short-circuits everything except `PhaseLogging` (`rulegroup.go:172`).

## 2. Module / package layout

Public root (importable):
- `coraza.go` / `waf.go` / `config.go` — façade + builder pattern (`WAFConfig`).
- `http/` — `net/http` middleware and a streaming-body interceptor (`http/middleware.go`, `http/interceptor.go`).
- `types/` — stable enums (`RulePhase`, `MatchData`, `Interruption`) and `types/variables/variables.go` re-exporting the internal `RuleVariable` enum.
- `collection/`, `debuglog/` — small abstract interfaces used across `internal/` and plugins.
- `experimental/` — `waf.go` exposes `WAFWithOptions`/`WAFCloser`/`WAFWithRules` (`experimental/waf.go:12-30`); `experimental/plugins/` is the plugin SPI (`actions.go`, `operators.go`, `transformations.go`, `bodyprocessors.go`, `directives.go`, `auditlog.go`) that just forwards `Register*` to the internal registries.

`internal/` (not importable outside the module):
- `corazawaf/` — engine core: `waf.go` (487 LoC), `transaction.go` (2550 LoC), `rule.go` (774 LoC), `rulegroup.go`, `body_buffer.go`, plus build-tag-gated companions (`rule_multiphase.go`, `casesensitive.go`, `rxprefilter_on.go`).
- `seclang/` — directive parser (`parser.go`, `directives.go` 1435 LoC, `directivesmap.gen.go`, `rule_parser.go` 684 LoC, plus a `generator/` that produces the map at `go generate`).
- `operators/`, `transformations/`, `actions/`, `bodyprocessors/` — registries, one file per built-in.
- `auditlog/`, `collections/`, `cookies/`, `corazarules/`, `corazatypes/`, `environment/`, `io/`, `memoize/`, `strings/`, `sync/`, `url/`, `variables/` — small focused helpers.
- `environment/` is the FS-access shim: `default.go` sets `HasAccessToFS = true`, `nofsaccess.go` sets it false under `//go:build no_fs_access` (`environment/default.go:15`, `environment/nofsaccess.go:8`).

## 3. SecLang parser

`internal/seclang/` is a hand-rolled line-oriented parser, not lex/yacc. `Parser.parseString` reads with `bufio.Scanner`, handling three quirks (`parser.go:101-147`): `#` comments, trailing-backslash line continuations, and backtick-delimited multi-line blocks used by `SecDataset name \`...\``. The collected line goes to `evaluateLine` which splits on the first space, lowercases the directive, special-cases `Include` (recursion-capped at `maxIncludeRecursion = 100`, `parser.go:21` / `parser.go:163-173`), and otherwise looks up `directivesMap[directive]` (`parser.go:175`).

The dispatch table is generated. `directives.go` has the implementations and a `//go:generate go run generator/main.go` line (`directives.go:4`); `directivesmap.gen.go` is the produced `map[string]directive` with 58 supported directives plus a small "Unsupported directives" tail (`directivesmap.gen.go:135-143`):

```
"secargumentseparator":     directiveUnsupported,
"seccookieformat":          directiveUnsupported,
"secruleupdatetargetbymsg": directiveUnsupported,
"secrulescript":            directiveUnsupported,
"secruleperftime":          directiveUnsupported,
"secunicodemap":            directiveUnsupported,
"sectmpdir":                directiveUnsupported,
```

`directiveUnsupported` is a no-op returning `nil` (`directives.go:323-325`) — load-the-conf compatibility, the directive is silently ignored. Notably `SecRuleScript` (Lua-backed dynamic rules in ModSecurity) is unimplemented; there is no embedded Lua VM anywhere in the tree.

`SecRule`, `SecAction`, `SecMarker` all delegate to `ParseRule(RuleOptions{...})` in `rule_parser.go`. The rule body itself is parsed in three stages:
1. `parseActionOperator` splits `VARIABLES "@op arg" "act1,act2"` honouring quoted/escaped strings (`rule_parser.go:451-484`, `cutQuotedString` at `:486`).
2. `RuleParser.ParseVariables` is a small state machine with four states `{var-name, key, regex, xpath}` handling `|` separation, `!` negation, `&` count, `/regex/` and `XML:/xpath/` syntaxes (`rule_parser.go:42-162`).
3. `ParseOperator` normalises bare patterns / `!`-prefixed forms into `[!]@op arg` then resolves via `operators.Get(op, opts)` (`rule_parser.go:167-216`).
4. `ParseActions` / `applyParsedActions` runs metadata actions first, merges with phase-specific defaults from `SecDefaultAction`, then attaches the rest (`rule_parser.go:271-327`).

`chain` handling is structural: when a parsed rule lands and the previous top-level rule had `HasChain = true` (`actions/chain.go:53`), `ParseRule` links it as `parent.Chain` rather than registering it in the group, and propagates the parent's `LogID_` (`rule_parser.go:422-443`). `SecMarker` produces a synthetic rule with `ID_ = 0` and `SecMark_` set, consumed by the `skipAfter` action at eval time (`directives.go:113-131`).

## 4. Operators + transformations

Registries are plain `map[string]factory`s with package-init self-registration:

- `internal/operators/operators.go:30` — `var operators = map[string]plugintypes.OperatorFactory{}` plus `Get` / `Register`.
- `internal/transformations/transformations.go:13` — same pattern, 34 transformations registered in `init()` (`transformations.go:30-65`).

Each built-in lives in its own file gated by a negative build tag, e.g. `//go:build !coraza.disabled_operators.detectSQLi` (`detect_sqli.go:4`), so an Envoy/WASM build can strip unused operators at compile time.

Three operator implementations to anchor the pattern:

**`@rx`** (`operators/rx.go`) — wraps the pattern in `(?s)` (dotall, ModSec parity) — `rx.go:67-78`, picks `binaryregexp` if the pattern contains non-UTF-8 byte escapes (`matchesArbitraryBytes`, `rx.go:80-85`, `:220`), and compiles via `memoizeDo(options.Memoizer, cacheKey, …)` so identical patterns across rules share one compiled `*regexp.Regexp` (`rx.go:94-117`). When `SecRxPreFilter On` is active it also computes `minMatchLength` + a literal-based prefilter and detects pure `^literal$` patterns for an NFA-bypass exact-match fast path (`rx.go:101-114`, `rx.go:139-147`). Capture mode uses `FindStringSubmatchIndex` and slices the input directly to avoid allocations, capping at the 9 capture groups ModSec exposes (`rx.go:149-172`).

**`@detectSQLi`** (`operators/detect_sqli.go`) — thin wrapper over `github.com/corazawaf/libinjection-go`; on hit it writes the libinjection fingerprint into capture-field 0 so rules can log `%{TX.0}` (`detect_sqli.go:40-46`). `@detectXSS` is the same shape, no fingerprint (`detect_xss.go:40-42`).

**`@beginsWith`** (`operators/begins_with.go`) — compiles its argument as a `macro.Macro` at init, then expands per-tx before `strings.HasPrefix` so the comparison value can reference `%{tx.foo}` etc. (`begins_with.go:33-52`). This macro-then-compare pattern is shared by `@contains`, `@endsWith`, `@streq`, `@within`, `@eq/@lt/@gt/@ge/@le`.

Transformations are simple `func(string) (string, bool, error)` returning the new value plus a "changed" flag used by the rule's transformation-cache key. Example: `lowerCase` is literally `strings.ToLower(data)` with a `data != transformed` flag (`transformations/lowercase.go:10-15`); `urlDecode` handles `%xx` and `+` with an in-place byte rewrite borrowed from senghoo/modsecurity-go (`url_decode.go:21-67`).

`tinygo` builds replace network-dependent operators with stubs that always match — e.g. `rbl_tinygo.go:11-18` and `inspect_file_tinygo.go:11-18` both `Register` a `&unconditionalMatch{}`, keeping the rule loadable but inert.

## 5. Transaction state machine + rule evaluation loop

`RuleGroup.Eval(phase, tx)` is the per-phase driver (`rulegroup.go:155-280`). It walks the flat `rg.rules` slice, skipping by `Phase_`, by `tx.ruleRemoveByID`/`ruleRemoveByIDRanges`, by `tx.SkipAfter` (consumes until matching `SecMarker`), by `tx.Skip` counter, and by `tx.AllowType` (`AllowTypePhase` aborts the current phase, `AllowTypeRequest` aborts request-side phases 1+2, `AllowTypeAll` aborts everything) — `rulegroup.go:208-253`. Per-phase `tx.stopWatches[phase]` is captured for audit log part `H`.

Each `Rule.Evaluate` allocates a fresh `collectiveMatchedValues` then calls `doEvaluate` recursively for chains (`rule.go:171-186`, `:190-`). For every variable in the rule's `r.variables`, `tx.GetField(rv)` resolves the value list — keyed lookup, regex-keyed lookup, or full enumeration depending on whether the rule used `VAR:key`, `VAR:/re/`, or bare `VAR` (`transaction.go:626-684`), then applies `tx.ruleRemoveTargetByID` exceptions in-place (`:656-671`), and finally collapses to a single count `MatchData` when the original syntax was `&VAR`. Each value is transformed (`r.transformArg` caches results by `transformationKey` in the per-tx cache that's reset between phases, `rulegroup.go:163-166`) and tested with `r.executeOperator`. On match, a `corazarules.MatchData` is materialised, `r.matchVariable(tx, md)` updates `MATCHED_VAR`/`MATCHED_VAR_NAME`/`MATCHED_VARS`, then `Msg`/`LogData` are `Macro.Expand`-ed against the now-updated tx (`rule.go:284-336`).

Chains are resolved depth-first only by the parent rule (`ParentID_ == noID` gate at `rule.go:353`): the parent walks `r.Chain` linked-list and re-enters `doEvaluate` on each (`:354-372`), only producing disruptive actions if *every* link matched. `setvar:` runs through `actions/setvar.go`, restricted to the `TX` collection (`setvar.go:79-87`), with parseable `+N`/`-N` arithmetic on the existing value (`setvar.go:149-184`).

Multi-phase evaluation (built-tag gated as `multiphaseEvaluation` via `rule_option_multiphase.go`) is a real optimisation: `rule_multiphase.go:44-230` defines `minPhase(v)` mapping each `RuleVariable` to the earliest phase it could possibly be populated (e.g. `RequestHeaders -> 1`, `Args -> 2`, `ResponseBody -> 4`), then `computeRuleChainMinPhase` (`:240-258`) lazily caches the minimum across a whole chain, letting `RuleGroup.Eval` evaluate a phase-2 rule already in phase 1 if all its variables are available — with `isMultiphaseDoubleEvaluation` (`:333-377`) bookkeeping so the anomaly score is not incremented twice for the same matched chain.

Variable resolution at match time goes through `tx.Collection(rv.Variable)`, which returns one of the typed collections in `internal/collections/` (`collection.Map`, `collection.Keyed`, `collection.Single`). The variable enum itself is in `types/variables/variables.go`.

## 6. OWASP CRS compatibility

Two main accommodations make the unmodified CRS load:

1. **Directive surface.** `directivesmap.gen.go` recognises every common ModSec directive; the seven that have no useful Go equivalent (Lua scripts, perf timers, Unicode maps, etc.) are wired to `directiveUnsupported` so loading does not error (`directivesmap.gen.go:135-143`). `SecRemoteRules` *is* implemented (`:30`), so CRS-as-URL works.
2. **Regex semantics.** `@rx` automatically prepends `(?s)` (dotall) under the historical compat mode and `(?sm)` (dotall + multiline) under the legacy default, "required by some CRS rules and matching ModSec behavior" (`operators/rx.go:67-78`). Non-UTF-8 byte escapes silently fall through to `rsc.io/binaryregexp` so CRS patterns like `\xc0\xae` compile (`rx.go:80-85`).

Concrete CRS gaps documented in code: the audit-log Part `D` ("intermediary response headers") and Part `G` ("response body") are explicit `not implemented yet` (`directives.go:872`, `:879`); `SecUploadKeepFiles`'s `RelevantOnly` mode is `not implemented yet` (`directives.go:884`); `SecRuleScript` is unsupported (no Lua engine). CRS testing is wired in `testing/coreruleset/coreruleset_test.go` which loads `coreruleset.FS` + `@crs-setup.conf.example` and runs the `coreruleset/go-ftw` runner against an `httptest` server — i.e. CRS conformance is gated by go-ftw, not a hand-rolled corpus.

There is also a multiphase double-evaluation guard specifically to avoid "incrementing the CRS anomaly score multiple times from the same variables chain" (comment at `rule.go:319-321`).

## 7. HTTP middleware integration

`http/middleware.go` is the only stdlib integration point and is excluded from tinygo (`//go:build !tinygo`, `middleware.go:5`). `WrapHandler(waf, h)` returns an `http.Handler` that, for every request:

1. Calls `waf.NewTransaction()` (or `NewTransactionWithOptions{Context: r.Context()}` if the WAF implements `experimental.WAFWithOptions`, `middleware.go:109-115`) and `defer`s `tx.ProcessLogging()` + `tx.Close()` so phase 5 runs even on panic-free early returns (`middleware.go:117-126`).
2. If `tx.IsRuleEngineOff()`, it short-circuits straight to the inner handler (`middleware.go:129-134`).
3. Calls `processRequest(tx, r)` which splits `req.RemoteAddr` into host/port, drives `ProcessConnection` → `ProcessURI(req.URL.String(), req.Method, req.Proto)` → adds every `req.Header`, the promoted `req.Host`, and *all* `req.TransferEncoding` values (the comment explicitly cites HTTP-smuggling / TE.TE-attack detection at `middleware.go:56-62`), then `ProcessRequestHeaders` and optionally `ReadRequestBodyFrom(req.Body)` swapping `req.Body` for a `MultiReader` that lets the inner handler still read it (`middleware.go:26-98`).
4. Wraps the `http.ResponseWriter` via `wrap(w, r, tx)` in `http/interceptor.go` to buffer the response, drives the inner `h.ServeHTTP`, then `processResponse` runs phases 3 + 4 (`middleware.go:147-155`).
5. On interruption it converts `it.Status` (defaulting to 403 for `deny`, `middleware.go:163-173`) into the response status code.

## 8. tinygo / WASM build target

The engine is explicitly designed to compile under TinyGo. Evidence:

- 51 files carry either `//go:build tinygo` or `//go:build !tinygo` tags. Net-stdlib-using paths are split into a default file and a tinygo stub: `internal/operators/rbl.go` vs `rbl_tinygo.go`, `inspect_file.go` vs `inspect_file_tinygo.go`, `validate_schema.go` vs `validate_schema_tinygo.go`. The tinygo stubs `Register` an `unconditionalMatch` so rules referencing those operators still load (`rbl_tinygo.go:11-18`).
- `http/middleware.go:4-5` is excluded from tinygo entirely with the comment "tinygo does not support net.http so this package is not needed for it".
- The `seclang` parser specifically avoids `defer` in `Parser.FromFile` "as tinygo does not seem to like it" (`parser.go:67`, `:74`, `:83`).
- `internal/environment/nofsaccess.go` is selected by `//go:build no_fs_access` and flips `HasAccessToFS` to false so the constructor skips the `IsDirWritable(waf.TmpDir)` precheck (`waf.go:36-40`, `environment/nofsaccess.go:8`).
- `internal/auditlog/init_tinygo.go`, `internal/memoize/nosync.go`, `internal/memoize/nosync_test.go` swap in single-threaded primitives, since proxy-wasm is single-threaded per VM.

The actual Envoy filter lives in a separate repo (`coraza-proxy-wasm`, referenced in `README.md:44`) — this repo provides the build-tagged engine it imports.

## 9. What's genuinely novel at the code level

- **Multi-phase variable-aware scheduling.** `rule_multiphase.go` precomputes a `minPhase()` for every variable and a chain-level `chainMinPhase` so phase-2 rules whose variables are all available in phase 1 can fire early, with `isMultiphaseDoubleEvaluation` performing chain-set comparison so anomaly scoring is not double-counted (`:240-377`). This is an evaluation strategy ModSecurity does not have.
- **Compile-time regex prefilter.** `internal/operators/rxprefilter.go` (1000+ LoC) parses each `@rx` pattern with `regexp/syntax`, extracts ordered/required literal sets, computes a minimum match length, and detects pure `^literal$` for an NFA bypass. Combined with the global `Memoizer` cache (`rx.go:94-117`) and shared across all WAF instances, this is targeted directly at CRS's enormous OR-of-literals rules.
- **Build-tag-driven operator pruning + tinygo stubs.** Every operator is independently strippable (`//go:build !coraza.disabled_operators.<name>`), and the entire engine compiles to TinyGo with deterministic graceful degradation — letting the same code run as a Go middleware *and* a proxy-wasm filter, which is what makes the project structurally distinct from a straight ModSec port.
