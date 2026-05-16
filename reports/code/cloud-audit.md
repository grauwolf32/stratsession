# cloud-audit — code-level analysis

Snapshot: `cloud-audit` v2.2.1, `src/cloud_audit/`. ~16 kLOC of typed Python (mypy strict), Pydantic v2 models, Typer CLI, boto3-only AWS access. No graph DB, no async — a single-process, thread-pool scanner.

## Architecture overview

Entry points are declared in `pyproject.toml:54-56`: `cloud-audit = "cloud_audit.cli:app"` (Typer app) and `cloud-audit-mcp = "cloud_audit.mcp_server:main"`. `__main__.py:3-5` re-exports `cli.app` so `python -m cloud_audit` works.

The hot path is `cloud_audit.scanner.run_scan` (`src/cloud_audit/scanner.py:85-229`):

1. Build a list of check callables via `provider.get_checks(...)`.
2. Pre-filter excluded checks (`scanner.py:107-113`).
3. Execute on a `ThreadPoolExecutor(max_workers=min(8, len(checks)))` with each check wrapped in `_execute_check` that captures exceptions into `CheckResult.error` (`scanner.py:65-82, 127-149`).
4. Post-scan, in order: suppressions, min-severity filter, `compute_summary`, then **lazy imports** of `correlate.detect_attack_chains`, `cost_model.estimate_*`, and `root_cause.compute_root_causes` (`scanner.py:165-227`). All three are wrapped in try/except so a failure in one stage does not kill the scan.

AWS access is centralised in `providers/aws/provider.py`. `AWSProvider.__init__` creates a `boto3.Session`, optionally calls `sts:AssumeRole` (`provider.py:84-94`), and exposes a thread-safe per-`(service, region)` client cache (`provider.py:97-130`) with `botocore Config(retries={"mode": "adaptive", "max_attempts": 5})` (`provider.py:42`). Region discovery on `--regions all` uses `ec2.describe_regions` filtered to opted-in regions (`provider.py:101-110`).

## Module / package layout

```
src/cloud_audit/
  cli.py               1597 LOC — Typer commands: scan, list-checks, list-frameworks,
                                  show-framework, demo, diff, trend, simulate, threat-feed, version
  scanner.py            229 LOC — run_scan orchestrator (thread pool + post-processing)
  correlate.py         1574 LOC — 31 attack-chain rules + relationship collection
  models.py             227 LOC — Pydantic models: Finding, CheckResult, ScanReport,
                                  AttackChain, EscalationPath, VizStep, CostEstimateData
  simulate.py           190 LOC — What-If simulator (pure in-memory replay)
  root_cause.py         223 LOC — group findings -> single-fix recommendations
  cost_model.py         516 LOC — breach-cost dollar estimates
  history.py            173 LOC — scan persistence under ~/.cloud-audit/
  diff.py               161 LOC — scan-to-scan delta
  config.py              96 LOC — YAML config (.cloud-audit.yml): suppressions, min_severity
  mcp_server.py         299 LOC — FastMCP server, 6 tools
  compliance/           engine.py + frameworks/ (CIS, SOC2, PCI, NIST etc.)
  providers/
    base.py             BaseProvider ABC + make_check helper
    aws/
      provider.py       AWSProvider, _CHECK_MODULES registry
      iam_analyzer.py   706 LOC — ESCALATION_METHODS catalog + action resolver
      iam_trust_graph.py 524 LOC — AssumeRole graph + BFS reachability
      checks/           23 modules (account, iam, s3, ec2, vpc, ...)
      threat_feed/      10 active-abuse pattern modules + registry
  reports/
    html.py + templates/report.html.j2  (Jinja2)
    sarif.py            SARIF v2.1.0 emitter
    markdown.py / compliance_markdown.py / diff_markdown.py / compliance_html.py
```

## Check plugin system

**No entry-point or decorator-based plugin registry.** Checks are plain functions discovered through a fixed module list `_CHECK_MODULES` in `providers/aws/provider.py:45-70`. Each module follows the same contract:

- `def check_<thing>(provider: AWSProvider) -> CheckResult` — implementation.
- `def get_checks(provider: AWSProvider) -> list[CheckFn]` — registration.

Registration is done with `make_check` (`providers/base.py:13-18`):

```python
def make_check(fn, provider, *, check_id, category):
    p = partial(fn, provider)
    p.check_id = check_id
    p.category = category
    return p
```

Concretely, S3 (`checks/s3.py:593-604`):

```python
def get_checks(provider):
    from cloud_audit.providers.base import make_check
    return [
        make_check(check_public_buckets, provider, check_id="aws-s3-001", category=Category.SECURITY),
        make_check(check_bucket_encryption, provider, check_id="aws-s3-002", category=Category.SECURITY),
        ...
    ]
```

`AWSProvider.get_checks` iterates `_CHECK_MODULES`, calls each `module.get_checks(self)`, and filters by `check_fn.category` if `--categories` was passed (`provider.py:151-161`). 23 service modules under `checks/` plus the threat-feed bundle register ~91 `make_check` callables; the README's 94 figure includes a few sub-checks emitted as multiple findings from one function.

**Concrete check pattern** (`checks/s3.py:66-150`, `check_public_buckets`):

1. Construct `CheckResult(check_id="aws-s3-001", check_name=...)`.
2. Use a per-scan module-level cache (`_list_buckets`, `s3.py:45-63`) to avoid re-listing buckets for every S3 check; the cache is dropped between scans by `AWSProvider.reset_caches()` (`provider.py:141-149`).
3. For each resource, on each negative condition, append a `Finding(severity=Severity.HIGH, ..., remediation=Remediation(cli=..., terraform=..., effort=Effort.LOW), compliance_refs=["CIS 2.1.5"])`.
4. Exceptions are caught and either translated into a Finding (e.g. `NoSuchPublicAccessBlockConfiguration` -> "no public access block") or swallowed for `AccessDenied`.

## Attack-chain correlation engine (31 rules)

Lives in `src/cloud_audit/correlate.py`. **Rules are plain Python functions, not data;** this is the central design choice and the reason rule logic can be heterogeneous.

Two function-pointer lists are dispatched (`correlate.py:1494-1529`):

- `_SIMPLE_RULES` (24 entries) — signature `(by_check) -> list[AttackChain]`, depend only on findings.
- `_RELATIONSHIP_RULES` (7 entries) — signature `(by_check, rels) -> list[AttackChain]`, also need EC2-instance-to-role, Lambda-to-role, and role-to-policies maps.

Rule count is exactly 31 (verified by counting `def _detect_` symbols). They are numbered `AC-01` through `AC-39` with some gaps.

`detect_attack_chains` (`correlate.py:1532-1573`) is the dispatcher: indexes findings by `check_id`, runs simple rules, then relationship rules if `relationships` is non-None, applies a hard-coded **suppression map** so that supersets hide subsets (`AC-10` masks `AC-09`, `AC-26` masks `AC-12`, `AC-36` masks `AC-07`) and sorts by severity.

Each rule directly constructs an `AttackChain` Pydantic model and embeds a list of `VizStep` nodes used by the HTML renderer to draw the chain diagram. Example — `_detect_exposed_admin_instance` (AC-01, `correlate.py:216-262`):

```python
sg_findings = by_check.get("aws-vpc-002", [])
open_sgs = {f.resource_id for f in sg_findings}
for instance_id, sgs in rels.ec2_sgs.items():
    if not (set(sgs) & open_sgs):
        continue
    role_name = rels.ec2_roles.get(instance_id, "")
    if role_name and _role_is_admin(rels, role_name):
        chains.append(AttackChain(chain_id="AC-01", ..., mitre_refs=["T1190","T1552.005","T1078.004"], ...))
```

The relationship-collection layer is opportunistic: `collect_relationships` (`correlate.py:85-122`) inspects which `check_id`s actually produced findings and only calls boto3 (`_collect_ec2_rels`, `_collect_lambda_rels`, `_collect_role_policies`) when those collectors are required by at least one finding.

## IAM privilege escalation graph (61 methods, 9 categories)

Split across two files. Both reuse the single `iam:GetAccountAuthorizationDetails` paginated call (`iam_analyzer.py:462-478`) — one API round-trip per scan.

### Action-based detector (`iam_analyzer.py`)

`ESCALATION_METHODS: dict[str, _MethodDef]` (`iam_analyzer.py:66-455`) is the data-driven catalog: 57 entries, each declaring `actions: list[str]`, `category: EscalationCategory`, `severity`, `target`. Examples: `"AttachUserPolicy"` requires `["iam:AttachUserPolicy"]`; `"PassRole+EC2"` requires `["iam:PassRole", "ec2:RunInstances"]`.

`resolve_principals` (`iam_analyzer.py:555-631`) expands inline policies + attached managed policies + group memberships into `(allowed_actions, denied_actions)` sets per principal, skipping `aws-service-role` and `service-role/AWS*` roles. `_action_matches` is `fnmatch.fnmatch(action.lower(), pattern.lower())` (`iam_analyzer.py:495-497`) — wildcards yes, but `NotAction` is explicitly skipped (`iam_analyzer.py:530-532`) and conditions (MFA, ExternalId, SourceArn) are not evaluated.

### Lateral movement via trust graph (`iam_trust_graph.py`)

This is the AssumeRole graph the README sells as PMapper-lite. Data structures (`iam_trust_graph.py:135-153`):

```python
@dataclass
class TrustEdge:
    source_arn: str         # principal ARN, "*", or "<acct>:root"
    source_kind: str        # AWS|Service|Federated|CanonicalUser|Wildcard
    target_role_arn: str
    target_role_name: str
    has_conditions: bool

@dataclass
class AssumeRoleGraph:
    edges: list[TrustEdge]
    role_admin_status: dict[str, bool]
    role_arn_to_name: dict[str, str]
    account_id: str
```

The graph is just an edge list. `_build_adjacency` (`iam_trust_graph.py:308-313`) builds `source_arn -> [TrustEdge]` lazily inside the search.

`build_assume_role_graph` (`iam_trust_graph.py:247-286`) parses every role's `AssumeRolePolicyDocument` via `parse_trust_policy` (only `Effect=Allow` statements whose Action contains `AssumeRole`), normalises bare 12-digit account IDs to `arn:aws:iam::<id>:root` (`_normalize_aws_principal`, `iam_trust_graph.py:231-244`), and marks each role admin or not via `_role_is_admin` which scans inline + attached + customer-managed policies for `Action: * + Resource: *` (`iam_trust_graph.py:166-214`).

`find_lateral_escalations` (`iam_trust_graph.py:488-523`) produces four method types — `AssumeRole:Direct`, `AssumeRole:Chain`, `AssumeRole:WildcardTrust`, `AssumeRole:CrossAccountRoot`. `Direct`/`Chain` is a BFS (`_find_chain_to_admin`, `iam_trust_graph.py:316-368`) capped at `_MAX_CHAIN_LENGTH = 5` nodes (= 4 hops). Same-account-`:root` semantics is handled by an expanded `neighbors()` helper that pulls in any role trusting `<our_account>:root` from any in-account node (`iam_trust_graph.py:329-339`).

Category count: nine entries in `EscalationCategory` (`models.py:126-137`). Method count: pyproject advertises 64, the catalog literal contains 57 action-based + 4 lateral = 61 in this revision (`iam_analyzer.py:13` says "61 detection methods across 9 categories"); the README and `__init__` description drift slightly.

## What-If simulator

`src/cloud_audit/simulate.py`. CLI entry `simulate` at `cli.py:1322-1448`, takes `--fix aws-iam-001,aws-vpc-002,...` (comma-separated check IDs) and either uses the persisted last report from `~/.cloud-audit/` or a `--report` file. **No AWS calls** — the function operates on a `ScanReport`.

`simulate_fix` (`simulate.py:72-142`):

1. **Findings:** build `reduced_findings = [f for f in report.all_findings if f.check_id not in fix_check_ids]`.
2. **Score:** `penalty = sum(SEVERITY_WEIGHT[f.severity] for f in reduced_findings); score_after = max(0, 100 - penalty)`. Weights at `simulate.py:21-27` are CRITICAL=20, HIGH=10, MEDIUM=5, LOW=2, INFO=0.
3. **Chains:** re-invokes `correlate.detect_attack_chains(reduced_findings, None)` — relationship-less mode, so only the 24 simple rules participate; `chains_broken = original - after` by `chain_id`.
4. **Risk:** `_compute_total_risk` sums `cost_estimate.low_usd/high_usd` over remaining chains.
5. **Next fix:** `_compute_next_fix` calls `root_cause.compute_root_causes(reduced_findings, after_chains)` and returns the top result.

This is what makes the simulator local: passing `relationships=None` short-circuits the relationship rules in `detect_attack_chains` (`correlate.py:1556-1559`) so no boto3 calls are ever needed. The trade-off — explicit in this code — is that simulation cannot break or keep relationship-dependent chains (AC-01, AC-02, AC-05, AC-07, AC-23, AC-24, AC-29).

## MCP server

File: `src/cloud_audit/mcp_server.py`. Framework: `mcp.server.fastmcp.FastMCP` (the upstream `mcp>=1.20.0` Python SDK, `pyproject.toml:40`). Transport: stdio (`mcp_server.py:295`). Tools registered with the `@mcp.tool()` decorator (auto-introspects signature). State is held in a module-global `_last_report_json` dict populated by `scan_aws` so subsequent tools query the cached report — no per-call rescan.

Six tools:

| Tool | Lines | Behaviour |
|---|---|---|
| `scan_aws(profile, regions, min_severity)` | `:53-111` | Builds `AWSProvider`, calls `run_scan`, caches `report.model_dump_json()`, returns summary dict. |
| `get_findings(severity, service, limit)` | `:114-159` | Filters cached findings by severity and by `check_id.split("-")[1]` (service prefix). |
| `get_attack_chains()` | `:162-189` | Returns chain id, name, severity, narrative, priority_fix, resources, finding count, USD risk. |
| `get_remediation(check_id)` | `:192-222` | Linear scan of cached findings, returns the first finding's CLI + Terraform + doc URL. |
| `get_health_score()` | `:225-249` | Returns the summary block only. |
| `list_checks()` | `:252-285` | No-AWS introspection: calls `module.get_checks(sentinel)` against `_CHECK_MODULES`. |

The wrapping is thin — every tool returns `json.dumps(...)` rather than typed objects, which matches FastMCP's text-tool convention.

## Threat Feed (v2.2)

10 modules under `src/cloud_audit/providers/aws/threat_feed/`. Registry: `threat_feed/__init__.py:55-66` (`_PATTERN_MODULES`). Each module is self-contained (~170–260 LOC) exporting `PATTERN_ID`, `CHECK_ID`, `PATTERN_NAME`, `PATTERN_SEVERITY`, `DOC_URL`, `def detect(provider) -> CheckResult`.

The 10 patterns: `ses_phishing`, `lambda_function_url`, `quarantine_policy`, `trufflehog_ua`, `cryptomining_role`, `mmdsv1_in_use`, `whoami_confusion`, `cloudtrail_tampering`, `roles_anywhere_abuse`, `datazone_overgrant`.

Registration goes through the same `make_check` plumbing as regular checks but with `category=Category.THREAT` (`threat_feed/__init__.py:74-91`).

**External references** are attached at finding construction time. `Finding` model has explicit fields `threat_pattern_id: str | None` and `references: list[str]` (`models.py:79-86`). Example: `cryptomining_role.py` declares a `_REFERENCES` list of three news/research URLs (`threat_feed/cryptomining_role.py:42-46`) and passes it as `references=_REFERENCES` on every emitted finding. The package also declares `THREAT_FEED_VERSION = "2026-Q2"` (`threat_feed/__init__.py:48`).

## Output formats

All renderers live in `src/cloud_audit/reports/` and consume a `ScanReport` Pydantic model:

- **HTML** — `reports/html.py:129` uses Jinja2 with the only template `report.html.j2`. Sorts findings, groups by category, base64-embeds the logo so the output is a single self-contained file.
- **SARIF** — `reports/sarif.py:110` emits SARIF v2.1.0 JSON; rules from unique check IDs, results from findings with stable `partialFingerprints` derived from `(check_id, resource_id)`.
- **Markdown** — `reports/markdown.py:19`.
- **Compliance Markdown / HTML / Diff Markdown** — used by the `compliance` engine and the `diff` CLI.

No plugin discovery; format selection is hard-coded in `cli._handle_format` (`cli.py:635-679`).

## What's genuinely novel at the code level

1. **Lazy, finding-driven relationship collection** (`correlate.collect_relationships`, `correlate.py:85-122`): the correlation engine inspects which `check_id`s actually fired before deciding to call `describe_instances` / `list_functions` / `list_attached_role_policies`. Other open-source AWS scanners typically either collect everything up front or never. This is the cheapest viable correlation layer for one-shot CLI use.
2. **Replayable in-process simulator** (`simulate.simulate_fix`): the rule engine accepts a `relationships=None` mode (`correlate.py:1556-1559`) specifically so simulation can re-run on a saved report without any AWS access. The cost is documented in the code itself — relationship-dependent chains (AC-01/02/05/07/23/24/29) can't be re-evaluated.
3. **Trust-graph + action-catalog hybrid** (`iam_analyzer` + `iam_trust_graph`): the action catalog is a flat data-driven dict (61 methods), the trust graph is a separately built edge list with bounded BFS (4 hops max). The two share the single `GetAccountAuthorizationDetails` payload, never call `iam:SimulatePrincipalPolicy`, and explicitly skip SCPs, permission boundaries, and trust-policy `Condition` evaluation — the trade-offs are stated in the module docstring (`iam_trust_graph.py:1-18`), not hidden.
