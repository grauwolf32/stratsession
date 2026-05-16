# Betterleaks — code-level analysis

Repo: `sources/appsec/betterleaks/` (Zach Rice; ex-Gitleaks). Go 1.25, single static binary. Module: `github.com/betterleaks/betterleaks` (`go.mod:1`).

## 1. Architecture overview

`main.go:11` installs a SIGINT handler and calls `cmd.Execute()`. The CLI uses Cobra (`cmd/root.go:45`) with subcommands `git` (`cmd/git.go:34`), `dir`/`file`/`directory` (`cmd/directory.go:21`), `github` (`cmd/github.go:15`), `stdin` (`cmd/stdin.go:17`), plus a hidden legacy `detect` (`cmd/detect.go:43`). Each command: `initConfig` → `Config()` → `Detector()` → instantiate a `sources.Source` → consume `detector.Run(ctx, src)` (returns `iter.Seq[Result]`) or the deprecated `DetectSource`.

End-to-end pipeline (`detect/detect.go`):

1. **Source** `Fragments(ctx, yield)` emits `sources.Fragment{Raw, StartLine, Attributes}`.
2. **Prefilter (attributes-only CEL)** — sources gate fragments via a `SkipFunc` from `Detector.SkipFunc` (`detect/detect.go:273`) calling `celenv.EvalPrefilter`.
3. **Aho-Corasick keyword scan** — `d.prefilter.Match(lowerBuf)` (`detect/detect.go:589`) maps matched keywords to candidate rule IDs via `Config.KeywordToRules` (`config/config.go:337`); rules with no keywords come from `NoKeywordRules` (`detect/detect.go:604`).
4. **Regex** — `r.Regex.FindAllStringIndex(currentRaw, -1)` (`detect/detect.go:672`).
5. **Decoding loop** — `codec.Decoder.Decode` re-feeds base64/hex up to `MaxDecodeDepth` (`detect/detect.go:619-633`).
6. **Filter (CEL, finding+attributes)** — global then per-rule (`detect/detect.go:821, 831`) calling `celenv.EvalFilter`.
7. **Validate (CEL with HTTP)** — if `r.CelProgram() != nil` and `--validation`, enqueue on `Detector.ValidationPool` (`detect/detect.go:408-419`).
8. **Emit** — buffered channel of 1000 (`detect/detect.go:351`), exposed as `iter.Seq[Result]` (`detect/detect.go:340`).

## 2. Package layout

| Package | Role |
|---|---|
| `cmd/` | Cobra wiring, one file per subcommand; `root.go` builds the `Detector` and wires CEL/validation flags. |
| `detect/` | `Detector`, pipeline, decoding (`codec/`), tiktoken loader, match-context extraction, baseline. |
| `config/` | TOML/Viper schema (`ViperConfig`), `Translate`, `Config.CompileCELFilters`, `Config.CompileValidation`, legacy-to-CEL translator (`translate_filters.go`). |
| `celenv/` | Three CEL environments (`prefilter.go`, `filter.go`, `validation.go`) and every CEL binding (`bindings_*.go`). |
| `validate/` | Worker `Pool`, sha256-keyed `Cache` w/ singleflight, `Result` (`status/reason/metadata`). |
| `sources/` | `Source` iface and impls: `Files`/`File` (recursive archives), `Git`/`ParallelGit`, `GitHub`, plus `scm/`. |
| `regexp/` | Engine abstraction (`Engine` iface) over stdlib (`Stdlib`) and `wasilibs/go-re2` (`re2/re2.go`). |
| `words/` | Embedded gzipped NLTK wordlist + naive substring scanner used by `failsTokenEfficiency`. |
| `httpclient/` | `RetryTransport` with shared pause/backoff and rate-limit state extraction; `auth.go` token helpers. |
| `report/` | `Finding` type and writers: `json`, `csv`, `junit`, `sarif`, Go-template. |

## 3. CEL filter engine (`celenv/`)

Library: `github.com/google/cel-go v0.27.0` (`go.mod:10`). **Three separate `cel.Env`s**, each with a narrow variable scope plus shared builtins, each with its own `map[string]cel.Program` compile cache guarded by `sync.RWMutex`:

- `PrefilterEnv` (`celenv/prefilter.go:24`) — only `attributes: map<string,string>` in scope (`prefilter.go:29`).
- `FilterEnv` (`celenv/filter.go:22`) — adds `finding: map<string,string>` (`filter.go:28`).
- `ValidationEnvironment` (`celenv/validation.go:69`) — adds `captures` and a `secret` alias variable (`validation.go:86-91`) plus HTTP/crypto/AWS bindings.

All three share `cel.OptionalTypes()`, `ext.Bindings()`, `ext.Strings()`, plus `filterBindings(tke)` (`celenv/bindings_filter.go:245`) which registers `matchesAny`, `containsAny`, `entropy`, `failsTokenEfficiency`. Compilation is `env.Compile → env.Program` (`prefilter.go:53`, `filter.go:51`, `validation.go:232`). Evaluation binds vars to `map[string]any` (`prefilter.go:75`, `filter.go:76`, `validation.go:268`) and casts the result; non-bool prefilter/filter result is an error.

Hot-path caches in the bindings: `regexCache sync.Map` keyed by joined pattern string (`bindings_filter.go:65`), `acTrieCache sync.Map` keyed by sorted term list (`bindings_filter.go:87`). A translated allowlist pays trie/regex build cost once.

## 4. BPE naturalness scorer (`words/` + tiktoken)

Tokenizer: `github.com/pkoukk/tiktoken-go v0.1.8` with the **`cl100k_base`** encoding (OpenAI GPT-4 tokenizer), loaded **offline**. `detect/tiktokenloader.go:13` embeds `assets/cl100k_base.tiktoken.gz` via `//go:embed`; `SetBpeLoader(&TiktokenLoader{})` is called once in `NewDetectorContext` (`detect/detect.go:203`) so tiktoken-go never touches the network.

Scoring lives in `celFailsTokenEfficiency` (`celenv/bindings_filter.go:221`):

```
tokens := tke.Encode(analyzed, nil, nil)
if len(words.HasMatchInList(analyzed, 5)) > 0 { return true }
threshold := 2.5; if len(analyzed) < 12 { threshold = 2.1; if no 4-letter word match: 2.5 }
return float64(len(analyzed))/float64(len(tokens)) >= threshold
```

Signal = chars-per-BPE-token ratio: prose tokenises efficiently (~3–4), random secrets do not. Combined with a dictionary check (`words.HasMatchInList`). Wired into CEL as `failsTokenEfficiency(string) → bool` (`bindings_filter.go:200`). `tokenEfficiency = true` on a rule is appended as `failsTokenEfficiency(finding["secret"])` to its filter expression (`translate_filters.go:53`).

`words/` ships an NLTK wordlist (`words/words.go:11`, `//go:embed words.txt.gz`); `loadWords()` decompresses lazily under `sync.Once`. `HasMatchInList` (`words/search.go:22`) is **not** Aho-Corasick despite the comment — it's a nested O(n²) substring loop into a `map[string]struct{}`.

## 5. Aho-Corasick keyword pre-filter

Library: `github.com/BobuSumisu/aho-corasick v1.0.3` (`go.mod:6`). Two uses:

- **Detector-wide rule prefilter** built once in `NewDetectorContext`: `*ahocorasick.NewTrieBuilder().AddStrings(maps.Keys(cfg.Keywords)).Build()` (`detect/detect.go:229`). Keywords are lowercased during `ViperConfig.translate` (`config/config.go:180-184`) and aggregated into `cfg.Keywords`. Hot path: lowercase fragment into a pooled buffer, `d.prefilter.Match(lowerBuf)` (`detect/detect.go:587-589`), then `Config.KeywordToRules[keyword]` (`config/config.go:337-347`). No-keyword rules come from `NoKeywordRules`.
- **CEL `containsAny`** builds per-term-list tries lazily into a global `sync.Map` (`bindings_filter.go:87-98, 145-149`). Input is lowercased before `trie.MatchFirstString`.

## 6. RE2 regex

Go's stdlib `regexp` already uses RE2 — no `regexp/syntax` workaround. Codebase adds an `Engine` indirection (`regexp/regexp.go:5-13`) so `--regex-engine` can switch between `Stdlib{}` (`regexp/stdlib.go:12`) and `RE2{}` (`regexp/re2/re2.go:11`, wrapping `github.com/wasilibs/go-re2`, a wasm build of the C++ RE2 library). RE2 is the default (`cmd/root.go:154`). Note: `go.mod:90` replaces `wasilibs/go-re2 v1.10.0 → github.com/betterleaks/go-re2 ...` — a Betterleaks fork; not diffed against upstream here. Linear-time guarantees apply either way.

## 7. Validators (`validate/` + `celenv/`)

CEL evaluation is **synchronous**; concurrency lives one level up.

- `validate.Pool` (`validate/pool.go:22`) spawns N workers (`--validation-workers`, default 10, `cmd/root.go:107`) reading `validationJob`s off a buffered channel (`pool.go:44`: `make(chan validationJob, workers*10)`).
- `Detector.Run` calls `ValidationPool.SubmitContext` (`detect/detect.go:410`) instead of emitting directly; the pool emits enriched findings via `p.Emit` (`pool.go:33, 106`).
- Per job, `Cache.GetOrDo` (`validate/cache.go:57`) is keyed by `sha256(ruleID || secret || sorted(captures))` (`validate/cache.go:32`). Concurrent callers are coalesced through `golang.org/x/sync/singleflight` (`cache.go:68`) — same secret never validated twice.
- Cache miss → `env.Eval(program, finding, captures)` (`pool.go:198` → `celenv/validation.go:253`).

CEL `http.get` / `http.post` bindings (`celenv/bindings_http.go:15-104`): build stdlib `*http.Request`, call `e.client.Do(req)`, cap body at `maxResponseBody = 1 << 20` (1 MB, `validation.go:22`, `bindings_http.go:43`), JSON-decode, return `{status, json, headers, body}` (`bindings_http.go:133`). Single `*http.Client` per env. Timeout is one client-level `--validation-timeout` (default 10s, `cmd/root.go:105`; applied at `detect/detect.go:239`).

**No built-in per-request retry/rate-limiter in the validation HTTP client.** `httpclient/transport.go:25` (`RetryTransport`) is feature-rich but wired only to the GitHub source. Validation rate-limit handling is intended to be expressed inside CEL via the `unknown()` helper (`validation.go:135`, which maps `status == 429` to `{"result":"unknown","reason":"rate limited"}`).

Other validation bindings: `aws.validate(key, secret)` does real SigV4 POST to STS GetCallerIdentity (`bindings_aws.go:47-72`); `crypto.{md5,sha1,hmac_sha256}`, `hex.encode`, `time.now_unix`, `json.string`, `obfuscate` (length+class-preserving redaction, `bindings_obfuscate.go`), and a name-allowlisted `env(name)` reader gated by `--validation-env-vars` (`bindings_env.go:32-47`).

## 8. Sources

All implement `sources.Source` (`sources/source.go:17`): `Fragments(ctx, yield FragmentsFunc) error`.

- **`Files`/`File`** (`sources/files.go`, `sources/file.go`): `filepath.WalkDir` (`files.go:33`), each file → `File` source reading via pooled `bufio.Reader` (`file.go:40`), split on safe boundaries. Recursive archive descent via `github.com/mholt/archives` up to `MaxArchiveDepth` (`file.go:144`). Emits `attrs[AttrPath] = fragPath` (`file.go:247`), `StartLine` (`file.go:292`), optional `AttrFSSymlink` (`file.go:302`).
- **`Git`** (`sources/git.go:328`): `git -C ... log -p -U0 ...` through `gitleaks/go-gitdiff` (`go.mod:8`). Pre-computes commit attrs — `git.sha`, `git.author_name`, `git.author_email`, `git.date`, `git.message`, `git.remote_url`, `git.platform`, `path`, `resource=git.patch_content` (`git.go:367-385`) — then `shouldSkipAttrs(s.ShouldSkip, commitAttrs)` (`git.go:387`) **before** spawning a goroutine: prefilter-skipped commits cost zero fragment allocation. Each `TextFragment` becomes `Fragment{Raw: txt.Raw(OpAdd), StartLine: int(NewPosition), Attributes: commitAttrs}` (`git.go:437-441`). `ParallelGit` (`sources/parallel_git.go:45`) shards commits across N workers.
- **`GitHub`** (`sources/github.go:233`): enumerates user/org/single via `go-github` REST + `shurcooL/githubv4` GraphQL; scans configurable resource types — repo git history (`scm.CloneToTempDir` + `Git`), Actions logs/artifacts, issues/PRs/comments (GraphQL), discussions, releases, gists. Per-resource attrs stamped by `wrapYieldWithAttrs` (`github.go:478`); resource discriminators in `sources/attribute.go:18-25`. REST/GraphQL go through `httpclient.RetryTransport`.
- **`stdin`** wraps `os.Stdin` as `*sources.File` (`cmd/stdin.go:41`).

## 9. Drop-in Gitleaks compatibility

Schema, format names, and discovery paths dual-track:

- Env var precedence chain `BETTERLEAKS_CONFIG → GITLEAKS_CONFIG → BETTERLEAKS_CONFIG_TOML → GITLEAKS_CONFIG_TOML` (`cmd/root.go:39-42`), resolved by `getEnvWithFallback` (`root.go:245`).
- `findConfigFile` (`root.go:254`) tries `.betterleaks.toml` then `.gitleaks.toml`; `findIgnoreFile` does the same for `.betterleaksignore` / `.gitleaksignore`.
- Allow-comments: `var allowSignatures = []string{"betterleaks:allow", "gitleaks:allow"}` (`detect/detect.go:51`).
- `Config` carries both `MinVersion` (Gitleaks) and `BetterleaksMinVersion`; `validateMinVersion` (`config/config.go:360`) cross-checks Gitleaks min-version against `version.GitleaksCompat`.
- TOML is parsed with Viper into `ViperConfig` (`config/config.go:32`) using exact Gitleaks field names: `id`, `description`, `regex`, `path`, `secretGroup`, `entropy`, `keywords`, `tags`, `[[rules.allowlists]]` (deprecated singular `[rules.allowlist]` still supported, `config.go:48`), `[[rules.required]]`. `ViperConfig.Translate` (`config/config.go:145`) compiles regexes, validates, then calls `c.translateLegacyFilters()` (`config/config.go:351`) which **converts legacy fields into CEL strings** so the new engine runs old rules verbatim:
  - `entropy = N` → `entropy(finding["secret"]) <= N` (`translate_filters.go:50`)
  - `[[allowlists]].regexes` → `matchesAny(finding[secret|match|line], [...])` (`translate_filters.go:115-125`)
  - `stopwords` → `containsAny(finding["secret"], [...])` (`translate_filters.go:129`)
  - paths/commits → prefilter (OR allowlists) or rule filter (AND allowlists) (`translate_filters.go:132-150`)
  
  Legacy fields are zeroed after translation (`translate_filters.go:62-65, 70`).

Net effect: an unmodified Gitleaks `.gitleaks.toml` parses, translates, and runs through the new CEL-driven pipeline without user-visible behavioural divergence.

## 10. What is genuinely novel at the code level

1. **One unified CEL surface for prefilter, per-match filter, and HTTP validation** — three `cel.Env` configurations (`celenv/prefilter.go:24`, `filter.go:22`, `validation.go:69`) sharing custom builtins, with the legacy Gitleaks allowlist/entropy DSL mechanically transpiled into CEL strings (`config/translate_filters.go`). Three ad hoc match-time mechanisms collapse into one auditable expression layer.
2. **BPE-token-efficiency as a first-class detection primitive** — embedded offline `cl100k_base` (`detect/tiktokenloader.go:13`, `detect/detect.go:203`) plus the chars-per-token ratio test (`celenv/bindings_filter.go:221`) exposed as `failsTokenEfficiency()` in CEL. Not aware of another OSS scanner using BPE token compressibility as a filter signal.
3. **Validator pool with sha256+singleflight result cache** — `validate/cache.go:32-89` deduplicates HTTP calls for repeated (rule, secret, captures) tuples and coalesces in-flight duplicates: a monorepo with the same leaked key in 500 files hits the upstream API once. Combined with the per-job composite-rule rollup (`validate/pool.go:113-179`), this is more sophisticated than Gitleaks's one-shot validation hooks.

## Uncertainties / caveats

- The CEL validator HTTP path has **no per-request retry/backoff** built in; rate-limit logic outside `httpclient/transport.go` (used by the GitHub source) appears to live inside the CEL via the `unknown()` helper (`validation.go:135`).
- `words.HasMatchInList` (`words/search.go:22`) is described as "Aho-Corasick-style" but is a naive nested substring loop; O(n²·L) for large secrets.
- `go.mod:90` replaces `wasilibs/go-re2` with a Betterleaks fork; not inspected here.
