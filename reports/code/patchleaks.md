# PatchLeaks — code-level analysis

PatchLeaks is a single-binary Go 1.25 web app (Gorilla mux + cookie sessions, 11k LOC across ~25 files) that diffs two source tarballs of a GitHub project, parses each modified file with `smacker/go-tree-sitter` for all 11 supported languages, expands the diff with the bodies of called non-builtin functions discovered via per-language mod-time-keyed AST caches and a lazy whole-repo function index, and feeds the result to one of four LLM backends (Ollama / OpenAI / DeepSeek / Anthropic) with optional NVD CVE matching.

```
$ ls sources/appsec/patchleaks/
ai_client.go            cwe_lookup.go                    metrics_tracker.go            tracked_io.go
ai_config.json          dashboard_stats_bench_test.go    middleware.go                 tree_sitter_extractors.go
analysis.go             dashboard_stats.go               models.go                     universal_indexer.go
analysis_summary.go     dashboard_stats_test.go          products/                     universal_indexer_test.go
builtin_detector.go     disk_tracker.go                  README.md                     utils.go
builtin_detector_test.go generate_message_id_test.go    run.sh
config.go               go.mod / go.sum                  saved_analyses/
cpu_throttle_stub.go    handlers.go                      scheduler.go
                        lazy_function_index.go           static/  templates/
                        main.go
```

11 135 lines of Go in a flat `package main` (no sub-packages). Two test files, no internal tooling. Templates are Go `html/template`, static assets are vendored Bootstrap/jQuery in `static/{css,js,webfonts}`.

## 1. Architecture overview

`main.go:37` is the single entry point. It (a) instantiates a CPU throttler (`InitCPUThrottler(50.0)`), (b) eagerly warms the builtin-function index via `GetBuiltinDetector()` (`main.go:41`), (c) generates a fresh random MD5 username/password printed to the banner (`main.go:62-63, 178-209`), (d) binds an `http.Server` on a free port and starts a background scheduler goroutine (`main.go:77`). Routes are registered in `setupRouter()` (`main.go:110-138`) with two subrouters: an open one for view/dashboard endpoints, and a `basicAuthMiddleware`+`rateLimitMiddleware` subrouter (`main.go:117-119`) for mutating actions.

The "analysis pipeline" — the same one for the products page, folder-compare page, and library auto-monitor — lives in `analysis.go:runProductsAnalysis` (`analysis.go:79`) and is shaped:

1. `downloadAndExtractVersion(repoURL, version)` (`analysis.go:246`) fetches `https://<repo>/archive/refs/tags/<v>.zip`, extracts to a `cache/<repo>_<version>/` directory, with `TrackCacheHit/Miss` accounting.
2. `compareDirectories(oldPath, newPath, extension)` (`analysis.go:437`) enumerates files in both trees and dispatches each modified pair to `compareSingleFile` → `generateUnifiedDiff` (`analysis.go:693`), which actually shells out to the system `diff -u` rather than computing diffs in Go.
3. `analyzeDiffsForVulnerabilities` (`analysis.go:792`) caps each diff at 1000 lines (`analysis.go:799-800`) and records a placeholder `AnalysisResult`.
4. `runAIAnalysisOnResults` (`analysis.go:813`) spawns `*aiThreads` workers, each calling `ExtractFunctionContext(filePath, diffContent, true, newPath)` (`analysis.go:858`) to prepend a `=== Function Context ===` block to the diff, then `GetAIAnalysis` (`ai_client.go:258`) which template-substitutes `{file_path}` and `{diff_content}` into the `main_analysis` prompt (`config.go:121-135`).
5. The AI text is regex-parsed by `parseAIResponseForVulnerabilities` (`analysis.go:731`) looking for literal lines like `Vulnerability Existed: yes`, severity is heuristically extracted, and CWEs are pulled out by `extractCWEsFromAIResponse` (`dashboard_stats.go:390`).

## 2. Module / package layout

Everything is `package main`. Logical grouping:

- HTTP / web — `main.go`, `handlers.go` (~21 handlers, `handlers.go:124-914`), `middleware.go`, `templates/*.html`.
- Pipeline — `analysis.go`, `analysis_summary.go`, `universal_indexer.go`.
- Tree-sitter — `tree_sitter_extractors.go` (2 921 lines, 11 languages).
- Per-language runtime helpers — `builtin_detector.go`, `lazy_function_index.go`.
- LLM I/O — `ai_client.go`, `config.go`, `ai_config.json`.
- NVD / CVE — `utils.go:458-497`, `models.go:84-149`, `cwe_lookup.go`.
- Background — `scheduler.go`.
- Bookkeeping / dashboards — `dashboard_stats.go`, `disk_tracker.go`, `metrics_tracker.go`, `tracked_io.go`, `cpu_throttle_stub.go`.

Dependencies (`go.mod`): only `gorilla/mux`, `gorilla/sessions`, `google/uuid`, and `smacker/go-tree-sitter` — no LLM SDKs, no XML libraries beyond stdlib, no diff library (the system `diff` binary is invoked).

## 3. tree-sitter integration for 11 languages

`tree_sitter_extractors.go:2-15` imports `smacker/go-tree-sitter` plus the eleven per-language grammar packages:

```go
tsc "github.com/smacker/go-tree-sitter/c"
tscpp ".../cpp"      tscsharp ".../csharp"
tsgolang ".../golang" tsjava ".../java"
tsjs ".../javascript" tsphp ".../php"
tspy ".../python"    tsruby ".../ruby"
tsrust ".../rust"    tsts ".../typescript/typescript"
```

`go-tree-sitter` is a CGO binding — each grammar is compiled into the Go binary as a C library. There is no runtime grammar loader; the language is picked by a `switch` on the file extension (`universal_indexer.go:19` `DetectLanguage` maps 11 sets of extensions).

For each language the file defines:
- a `<lang>FileCache struct { src, tree, root, modTime, funcIndex, methodIndex }` keyed by file path with a `sync.RWMutex` (e.g. `tree_sitter_extractors.go:23`, `:118`, `:199`, …).
- a `build<Lang>Index(root, src)` walker that records every top-level function-defining AST node by name (e.g. PHP `function_definition` & `method_declaration` at `:45,:55`; Python `function_definition`+`identifier` at `:137-141`; C `function_definition`+`function_declarator` at `:218`; Go `function_declaration` at `:300`; Rust `function_item` at `:371`; Java/C# `method_declaration` at `:734`/`:663`; Ruby `method` at `:805`).
- a `getOrParse<Lang>File(filePath)` that stats the file, returns the cached parse if `modTime` matches, otherwise calls `p.SetLanguage(ts<lang>.GetLanguage()); p.Parse(nil, src)` and re-indexes.
- public `TSFind<Lang><Func|Method>`, `TSList<Lang>Functions`, `TSListCalledFunctions<Lang>`, plus per-language `collect<Lang>CallNames` walkers that key on `call_expression` (C/C++/Go/JS/TS/Rust), `method_invocation` (Java), or PHP's three call AST kinds (`function_call_expression`, `method_call_expression`, `scoped_call_expression`, `member_call_expression`).

The signature/body split is brittle: most languages just locate the first `{` and last `}` substring inside the matched node text (e.g. `tree_sitter_extractors.go:867-877` for PHP). Python uses the first newline instead.

`identifyChangedFunctionsFromDiff` (`universal_indexer.go:134`) lists every function in the new file, then keeps the ones whose lowercased name appears in the diff text as a `\b…\b` regex match — the heuristic for "which functions were touched". If tree-sitter parsing fails entirely, `extractFunctionCallsFromDiff` (`universal_indexer.go:263`) falls back to per-language regexes.

## 4. Builtin-function index

`builtin_detector.go:32-48` creates a single `BuiltinDetector` and kicks off `initialize()` in a goroutine. Initialize calls ten per-language loaders (`:55-64`). Four of them attempt to shell out to the real runtime and only fall back to a hard-coded list on failure:

- PHP: `exec.Command("php", "-r", "echo json_encode(get_defined_functions()['internal']);")` (`builtin_detector.go:106`). Always adds a "language constructs" hard-list first (`array`, `list`, `echo`, `print`, `die`, `exit`, `empty`, `isset`, `unset`, `eval`, `include*`, `require*`) because these are *not* in `get_defined_functions`.
- Python: tries `python3 -c "import json, builtins; print(json.dumps([x for x in dir(builtins) if callable(...) or x in ['__import__','__build_class__']]))"` then falls back to `python` before the hard-coded list.
- Ruby: `ruby -e "puts (Kernel.methods + Object.instance_methods + Array.instance_methods + Hash.instance_methods).uniq.sort"` (`:327`) — the union of four built-in classes' method tables.
- Go: `exec.Command("go", "doc", "builtin")` is invoked but its output is discarded (`:286-289`, `_ = output`) — only the hard-coded list of 23 builtins is actually used. This looks like an unfinished implementation.

The remaining languages (JavaScript/TypeScript, C, C++, C#, Java, Rust) use only the static lists embedded in the file. The detector is consulted in `ExtractFunctionContext` (`universal_indexer.go:71`) — builtins are skipped so the LLM context is not bloated with `printf`/`strlen`/etc.

## 5. Language-aware constructs

- **PHP language constructs.** Hand-listed at `builtin_detector.go:99-102` because `array`, `isset`, `echo`, `print`, `die`, `exit`, `empty`, `unset`, `eval`, `include*`, `require*` are syntactic forms that `get_defined_functions()` does not report.
- **Rust macros.** `loadRustBuiltins` (`builtin_detector.go:371-383`) registers both forms (`println!` *and* `println`, `vec!` *and* `vec`, etc.) so that whether the call extractor strips the `!` or not, lookup still hits.
- **Ruby `?` predicates.** Test asserts `IsBuiltin("ruby", "nil?") == true`; this works because the Ruby loader scrapes method names directly via `Kernel.methods + Object.instance_methods …` and `nil?`, `frozen?`, `tainted?`, etc. come out of those tables verbatim with the `?` preserved.
- **Python `__dunder__`.** The Python extractor explicitly forces `__import__` and `__build_class__` into the JSON list; without that they'd be filtered out by the `callable(getattr(builtins, x, None))` test on some interpreter versions.

## 6. Multi-LLM backend

`ai_client.go:16-27` defines `AIServiceClient{config, service, timeout}`. The abstraction is a single `GenerateResponse(prompt)` method (`ai_client.go:28-79`) that retries up to `MaxRetryAttempts = 3` times with `calculateBackoff` doubling each retry (cap 60 s); HTTP 429 / `"rate limit"` substrings trigger an additional backoff sleep.

Dispatch is a `switch client.service` (`ai_client.go:50-61`) into four per-provider methods, each hard-codes the request shape:

- `ollamaRequest` (`:107`) → POSTs `{model, prompt, stream:false, options:{temperature,num_ctx}}` to `<url>/api/generate` and reads `result["response"]`.
- `openAIRequest` (`:134`) → POSTs OpenAI chat-completions body `{model, messages:[{role:"user",content:prompt}], temperature, max_tokens}` to `<base_url>/chat/completions` with `Authorization: Bearer …`.
- `deepSeekRequest` (`:170`) — byte-for-byte identical to OpenAI, just different config keys; treated as an OpenAI-API-compatible provider.
- `claudeRequest` (`:206`) → POSTs `{model, max_tokens, temperature, messages:[…]}` to `<base_url>/messages` with `x-api-key` and `anthropic-version: 2023-06-01` headers; reads `result["content"][0]["text"]`.

`Config` in `config.go:8-17` keeps four parallel `map[string]interface{}` blobs (`Ollama`, `OpenAI`, `DeepSeek`, `Claude`), and `DefaultConfig` (`config.go:84-118`) seeds defaults (Ollama at `localhost:11434` with `qwen2.5-coder:3b`, GPT-4-turbo, deepseek-chat, claude-3-opus-20240229). No streaming and no tool-use is supported for any provider.

## 7. CVE matching

Two distinct CVE paths exist.

**Manual CVE list.** When the user supplies `cve_ids=CVE-1,CVE-2,…`, `runAIAnalysisOnResults` (`analysis.go:833-842`) pre-fetches each description by *scraping the NVD detail HTML page* — `GetCVEDescription` (`ai_client.go:273-323`) GETs `https://nvd.nist.gov/vuln/detail/<id>` and string-matches `data-testid="vuln-description"` then the next `</p>` to extract the description. For every diff file it then runs `AnalyzeWithCVE` (`ai_client.go:324`) which substitutes `{ai_response}` and `{cve_description}` into the `cve_analysis` prompt. The reply is regex-classified by `parseAICVEResponse`. If any file matches `Yes`, `GenerateCVEWriteup` (`ai_client.go:334-350`) substitutes the matching files' analyses into the third prompt `cve_writeup` (`config.go:142-169`), producing a markdown article with Background / Technical Details / Patch Analysis / PoC Guide / Recommendations sections.

**CPE-driven CVE list.** When a `LibraryRepo` has a `CPE` field set, `runCVEBasedAnalysis` (`utils.go:559-601`) calls `getCVEsForVersion(cpe, oldVersion)` → `fetchCVEsFromNVD(cpeName)` which hits the proper API `https://services.nvd.nist.gov/rest/json/cves/2.0?cpeName=…` with the configured `apiKey` header (`utils.go:458-491`), discovers every CVE that affected `oldVersion`, joins their IDs into `params["cve_ids"]`, and feeds the result into the same downstream pipeline.

## 8. Library mode + auto-monitoring

`startScheduler` (`scheduler.go:9-16`) fires a goroutine immediately and again every 30 minutes. `checkForNewVersions` (`:17-79`) loads `products/library.json` (a `[]LibraryRepo`, `models.go:63-73`), filters `AutoScan == true`, and runs `*aiThreads` workers each calling `getGitHubVersionsByDate(repo.RepoURL)`.

`getGitHubVersionsByDate` (`utils.go:188`) — interestingly — does *not* use the GitHub REST API. It hits `<repoURL>/refs?tag_name=&experimental=1` with browser-style `User-Agent`/`X-Requested-With: XMLHttpRequest` headers — this is GitHub's undocumented internal tag-autocomplete endpoint used by the web UI, so no token is needed but the call is rate-limited per IP.

If `repo.LastVersion` differs from the freshest tag, `getNextIncrementalVersion` (`utils.go:498-522`) picks the *next* version sharing the same base prefix (e.g. `1.2.3-beta` → `1.2.3-rc`) rather than the bleeding edge, and `triggerAutoAnalysis` (`scheduler.go:80-102`) creates an analysis record. If `repo.CPE != ""` the mode is `cve_auto` (NVD CPE lookup); otherwise it is `library_auto`. Auto-analyses run with `enable_ai: "on"` unconditionally.

The "diff cache" is the version-tarball cache in `analysis.go:downloadAndExtractVersion`. It is on-disk under `cache/<repo>_<version>/`, hit by `os.Stat`, and pruned by `cleanOldCache(30 days)`. On top of that, tree-sitter parse results are cached in-memory keyed by `filePath` + `modTime` for every language, and `LazyFunctionIndex` (`lazy_function_index.go:19-36`) keeps per-repo `cache map[lang:funcName]*FunctionDefinition`, `misses map[lang:funcName]bool`, and a `fileMightContainFunction` bufio.Scanner pre-filter that does a substring grep before paying for the tree-sitter parse.

## 9. What's genuinely novel at the code level

(a) Bootstrapping the *builtin* list by `exec.Command` against the user-installed language runtimes (`php`, `python3`, `ruby`) and only using the hard-coded fallback when that exec fails — this is unusual; most static analysers ship a frozen list. (b) The "skip if builtin → otherwise lazily search the whole repo with a substring pre-filter and an mod-time-keyed AST cache" pattern in `lazy_function_index.go` is a pragmatic way to enrich a diff with one-hop call graph context per LLM request without ever building a full index up-front. (c) Using GitHub's internal `<repo>/refs?experimental=1` endpoint instead of the REST API means the auto-monitor works with no GitHub token but is undocumented and fragile.
