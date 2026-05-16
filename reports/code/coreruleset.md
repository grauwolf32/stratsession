# OWASP Core Rule Set — code-level analysis

## 1. Repo structure

Top-level layout (`sources/appsec/coreruleset/`):

- `rules/` — **29 `.conf`/`.conf.example` files, ~14,348 LOC total** (`wc -l rules/*.conf*`). Holds every shipped CRS rule plus 19 `.data` files (newline-delimited token lists fed to operators such as `@pmFromFile`, e.g. `rules/scanners-user-agents.data`, `rules/unix-shell.data`, `rules/lfi-os-files.data`).
- `regex-assembly/` — `.ra` source files (~100+, e.g. `regex-assembly/942140.ra:1`) compiled into the giant `@rx` patterns embedded in the `.conf`. Each `.ra` declares flags like `##!+ i` and one literal per line; `crs-toolchain regex update <id>` regenerates the `@rx` blob in the conf (see comment at `rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf:72`).
- `plugins/` — extension hook. Ships only stub files (`plugins/empty-before.conf`, `empty-after.conf`, `empty-config.conf`, all empty) plus `plugins/README.md` pointing at the external plugin-registry.
- `tests/` — `tests/regression/` (pytest + FTW driver), `tests/integration/`, `tests/logs/` (golden modsec2-apache and modsec3-nginx logs). 25 per-file subdirs and **319 YAML cases** under `tests/regression/tests/`.
- `util/` — supporting tooling: `util/crs-rules-check/rules-check.py` (static linter), `util/APPROVED_TAGS` (governance: any tag used must appear here), `util/FILENAME_EXCLUSIONS`, `util/php-dictionary-gen/` (generator for `rules/php-function-names-933150.data`).
- `docs/` — only a stub README pointing to coreruleset.org.
- Root config: `crs-setup.conf.example` (the single user-tunable file).

## 2. Rule numbering scheme

Every rule has a 6-digit ID of form `9CCNNN` where `CC` is the rule-class block and `NNN` is the per-file rule. The convention is enforced by file naming. Observed ranges (filename → ID block):

| Range | File | Purpose |
|---|---|---|
| `900xxx` | `rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf.example` | User per-transaction exclusions (`ctl:`) |
| `901xxx` | `rules/REQUEST-901-INITIALIZATION.conf:54` | Variable init, defaults, sampling |
| `905xxx` | `rules/REQUEST-905-COMMON-EXCEPTIONS.conf` | Built-in false-positive suppression |
| `911xxx` | `rules/REQUEST-911-METHOD-ENFORCEMENT.conf:28` | HTTP method allow-list |
| `913xxx` | `rules/REQUEST-913-SCANNER-DETECTION.conf` | UA-based scanner detect |
| `920xxx` / `921xxx` / `922xxx` | `REQUEST-92x-PROTOCOL-*` | Protocol enforcement / attack / multipart |
| `930-934xxx` | `REQUEST-93x-APPLICATION-ATTACK-{LFI,RFI,RCE,PHP,GENERIC}` | Injection families |
| `941xxx` / `942xxx` / `943xxx` / `944xxx` | XSS / SQLi / session-fix / Java | Application attacks |
| `949xxx` | `rules/REQUEST-949-BLOCKING-EVALUATION.conf:225` | Inbound threshold decision |
| `950-956xxx` | `rules/RESPONSE-95x-DATA-LEAKAGES-*` / `RESPONSE-955-WEB-SHELLS.conf` | Outbound leakage |
| `959xxx` | `rules/RESPONSE-959-BLOCKING-EVALUATION.conf` | Outbound threshold decision |
| `980xxx` | `rules/RESPONSE-980-CORRELATION.conf:36` | Final score aggregation / audit log |
| `999xxx` | `rules/REQUEST-999-COMMON-EXCEPTIONS-AFTER.conf`, `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf.example` | Late/user exclusions |

Within each file the last three digits also encode internal slots: `xxx0xx`-`xxx018` are reserved for paranoia-level skip markers (e.g. `REQUEST-942-...:17` uses `942011`/`942012` for the PL1 `skipAfter` gates), keeping the real detection rules at `xxx100+`.

## 3. Anomaly scoring

CRS does not block on first match; it accumulates a score and decides at the end. The mechanism has three pieces:

**Initialisation.** `rules/REQUEST-901-INITIALIZATION.conf:309-337` declares one giant `SecAction` (id `901200`, phase 1) that zeroes every score variable: `tx.blocking_inbound_anomaly_score`, four `tx.inbound_anomaly_score_pl{1..4}` buckets, per-category counters `tx.sql_injection_score`, `tx.xss_score`, `tx.rfi_score`, `tx.lfi_score`, `tx.rce_score`, `tx.php_injection_score`, `tx.http_violation_score`, `tx.session_fixation_score`, the outbound mirror set, and finally `tx.anomaly_score=0`. Severity-to-weight defaults are also seeded here: `tx.critical_anomaly_score=5` (`:153`), `error=4` (`:162`), `warning=3` (`:171`), `notice=2` (`:180`), with inbound threshold `tx.inbound_anomaly_score_threshold=5` (`:83`) and outbound `=4` (`:93`).

**Increments.** Every attack rule ends with a two-line `setvar` pair, incrementing both the per-category and the per-PL bucket. Example, `rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf:65-66` (rule `942100`, libinjection detector):

```
setvar:'tx.inbound_anomaly_score_pl1=+%{tx.critical_anomaly_score}',
setvar:'tx.sql_injection_score=+%{tx.critical_anomaly_score}'
```

So a single libinjection hit adds 5 to PL1 and 5 to the SQLi category — sub-threshold on its own. Two independent SQLi rules tripping crosses the default threshold.

**Aggregation and decision.** `rules/REQUEST-949-BLOCKING-EVALUATION.conf:20-98` sums `tx.inbound_anomaly_score_pl{1..4}` into `tx.blocking_inbound_anomaly_score`, but only the PL buckets whose level `<= tx.blocking_paranoia_level` are added (one gated `SecRule` per level). The actual block is `:225`:

```
SecRule TX:BLOCKING_INBOUND_ANOMALY_SCORE "@ge %{tx.inbound_anomaly_score_threshold}" \
    "id:949110, phase:2, deny, ..."
```

with an earlier-phase variant `949111` (`:212`) that fires in phase 1 only when `tx.early_blocking=1`. `RESPONSE-980-CORRELATION.conf:36-37` finally composes `tx.anomaly_score = blocking_inbound + blocking_outbound` for audit logging.

## 4. Paranoia levels

Four levels (1=default, 4=aggressive) selected by `tx.blocking_paranoia_level` (initialised to 1 at `rules/REQUEST-901-INITIALIZATION.conf:123`), with a separate `tx.detection_paranoia_level` (`:133`) defaulting to the same value; `901500` (`:482`) refuses to start if detection PL < blocking PL.

Higher PL adds rules, never removes them — and it does so via a single uniform pattern. Every rule file opens with PL-1 skip markers and inserts more markers between each PL block, e.g. `rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf:17-18`:

```
SecRule TX:DETECTION_PARANOIA_LEVEL "@lt 1" "id:942011,phase:1,pass,nolog,...,skipAfter:END-REQUEST-942-APPLICATION-ATTACK-SQLI"
SecRule TX:DETECTION_PARANOIA_LEVEL "@lt 1" "id:942012,phase:2,...,skipAfter:END-REQUEST-942-APPLICATION-ATTACK-SQLI"
```

with analogous `@lt 2` (`:640-641`), `@lt 3` (`:1675-1676`), `@lt 4` (`:1941-1942`) before each PL block. Individual detection rules are tagged `paranoia-level/N` (e.g. `:58`, `:670`) and increment the matching `tx.inbound_anomaly_score_plN` bucket; combined with the PL-gated summation in `949` this means a rule tagged `paranoia-level/3` literally cannot block a transaction whose `blocking_paranoia_level=1` even if its `setvar` runs in detection mode. The same gating template repeats in every request/response file (`REQUEST-911-METHOD-ENFORCEMENT.conf:17`, `RESPONSE-980-CORRELATION.conf:104`, etc.) — a deliberate copy-paste convention rather than an abstraction.

## 5. Exclusion mechanisms

Two reserved files frame the rule chain, both shipped as `.example` so user edits survive upgrades — `rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf.example` and `rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf.example`. The header (`:58-73`) codifies which directive belongs where based on a ModSecurity quirk: per-transaction `ctl:` actions go in `900` (must precede the affected rule), startup-context `SecRuleRemoveById` / `SecRuleUpdateActionById` go in `999` (must follow the affected rule).

Typical idioms from the same file:

- Drop one ARG from one rule: `ctl:ruleRemoveTargetById=942100;ARGS:password` (`:111`).
- Drop an ARG from a whole attack class via tag: `ctl:ruleRemoveTargetByTag=attack-sqli;ARGS:pwd` (`:127`).
- Disable the engine for a known scanner IP: `ctl:ruleEngine=Off` (`:96`).
- Disable an ID range: `ctl:ruleRemoveById=941000-942999` (`:164`) — with caveat that libmodsecurity v3 does not yet support ranges in `ruleRemoveById`.

The fact that every CRS rule carries `tag:'OWASP_CRS'` (e.g. `REQUEST-901-INITIALIZATION.conf:62`) is what makes the wildcard form `ctl:ruleRemoveTargetByTag=OWASP_CRS;ARGS:pwd` (`:145`) work — exclusion by tag is the encouraged path. User data files (`.data`) live next to the rules and are loaded by reference; users tune by editing them rather than the rule.

## 6. Inclusion / chained rule patterns

`chain` glues a primary rule to one or more conditions that must all match (logical AND across the chain); only the head rule carries metadata. The full `initcol` block at `rules/REQUEST-901-INITIALIZATION.conf:352-366` is a triple-`chain` example. `SecAction` is the unconditional sibling, used purely to run `setvar` side-effects (e.g. the scoring init at `:309`, the PL-2 score-reset at `REQUEST-949-...:102`).

Walk-through — rule `941100` (libinjection XSS, `rules/REQUEST-941-APPLICATION-ATTACK-XSS.conf:83-102`):

```
SecRule REQUEST_COOKIES|REQUEST_COOKIES_NAMES|REQUEST_HEADERS:User-Agent|ARGS_NAMES|ARGS|XML:/* "@detectXSS" \
    "id:941100, phase:2, block, \
    t:none,t:utf8toUnicode,t:urlDecodeUni,t:htmlEntityDecode,t:jsDecode,t:cssDecode,t:removeNulls, \
    ... tag:'attack-xss', tag:'paranoia-level/1', ..., severity:'CRITICAL', \
    setvar:'tx.xss_score=+%{tx.critical_anomaly_score}', \
    setvar:'tx.inbound_anomaly_score_pl1=+%{tx.critical_anomaly_score}'"
```

Anatomy: **variables** (left-side, pipe-separated target list) → **operator** `@detectXSS` (libinjection bridge) → **action list**: id, phase, disposition, **transformations** (the `t:` chain — order matters and is applied left-to-right before matching), tags (one of which gates PL), severity, and the two-pronged anomaly increment. Compare with `942100` SQLi (`REQUEST-942-...:46-66`): same skeleton, `@detectSQLi` operator, different transformation chain (`t:utf8toUnicode,t:urlDecodeUni,t:removeNulls`), increments `sql_injection_score` instead. Rules `942140` (`:77-96`) and `942151` (`:110-129`) show the regex-assembly pattern: literally one `@rx` whose source-of-truth lives in `regex-assembly/942140.ra` / `942151.ra`.

## 7. Plugin system

`plugins/` is purely a load-point convention. The three shipped files are empty stubs whose only job is to exist so the webserver's `Include` directive can wildcard them without breaking on a missing file (`plugins/empty-before.conf`, `empty-after.conf`, `empty-config.conf` are all 0 bytes). `plugins/README.md` redirects users to the external `coreruleset/plugin-registry` GitHub org. A plugin is conventionally three files: `<name>-config.conf` (sets variables), `<name>-before.conf` (rules running before CRS, slot ~9510000), `<name>-after.conf` (after CRS). IDs `9500000-9999999` are reserved for plugins out of the main rule range. The system is filesystem-deployment, not a runtime API: there is no plugin loader code in this repo.

## 8. Test corpus

`tests/regression/CRS_Tests.py` is a pytest harness that consumes the **FTW** YAML format (Framework for Testing WAFs, `requirements.txt` pins `ftw==1.3.0`). YAML schema: top-level `meta` + `rule_id`, then a list of `tests:` each with `stages:` containing `input:` (raw HTTP — `headers`, `method`, `uri`, `data`, `version`) and `output:` assertions (`log: expect_ids: [...]` or `status:`). See `tests/regression/tests/REQUEST-942-APPLICATION-ATTACK-SQLI/942100.yaml:1` for a canonical example. There are 25 per-file test directories and **319 YAML files** under `tests/regression/tests/` (one per rule ID — the SQLi directory alone holds 60).

What makes the test suite portable across WAF engines: `tests/regression/coraza-overrides.yaml`, `httpd-overrides.yaml`, and `nginx-overrides.yaml` patch per-test expectations for engine-specific HTTP behaviour without forking the canonical YAML. E.g. `coraza-overrides.yaml:8-12` rewrites the expected status of `920100` test 4 from Apache's 400 to Coraza's 404 ("Coraza not reached - 404 page not found"). The same rules thus get validated against ModSecurity 2 (Apache), ModSecurity 3 (Nginx), and Coraza (Go) from one source corpus.

## 9. What's genuinely novel at the code level

What makes CRS the *de facto* standard is not the rules themselves but the **conventions that turn a ruleset into a managed product**:

1. **Engine-neutral source format.** The rules live in a portable SecLang dialect and are validated against three independent engines (ModSec2/Apache, ModSec3/Nginx, Coraza/Go) by the same YAML corpus with per-engine override files — so any third party can ship a SecLang-compatible WAF and inherit the entire ruleset for free (`tests/regression/coraza-overrides.yaml`, `nginx-overrides.yaml`).
2. **Tuning surface separated from rule body.** The `.example` exclusion files, the `tag:'OWASP_CRS'` on every rule (`REQUEST-901-INITIALIZATION.conf:62`), the `.data` files, and the documented `ctl:ruleRemoveTargetByTag` idioms (`REQUEST-900-...:145`) mean operators tune in their own files and `git pull` upgrades never overwrite local policy.
3. **Compile-time vs deploy-time controls.** Two orthogonal knobs — anomaly thresholds (operator-defined risk tolerance) and paranoia levels (operator-defined false-positive tolerance) — gate the same rules with the same uniform `skipAfter` template in every file. The result is one ruleset that can be deployed in monitor-only, low-FP, or maximum-detection modes from a single config variable, without touching the rules.
