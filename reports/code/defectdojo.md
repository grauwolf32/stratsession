# DefectDojo — code-level analysis

Source root analyzed: `sources/appsec/defectdojo/`. Single Django project (`dojo/`) registered as one app (`app_label = "dojo"`), Celery worker + beat, Postgres (default) or MySQL.

## 1. Architecture overview

The entire system is one Django app, `dojo`, mounted from `dojo/wsgi.py` / `dojo/manage.py`. Settings live in `dojo/settings/settings.dist.py` (4k+ lines) and are driven almost entirely by `DD_*` env vars (`dojo/settings/settings.dist.py:131-368` for the DB block). Default DB is `django.db.backends.postgresql` but the engine string is configurable, so MySQL/MariaDB are tolerated (`dojo/settings/settings.dist.py:359`).

`INSTALLED_APPS` is small and revealing — only `dojo` plus integrations (`dojo/settings/settings.dist.py:736-763`): `watson` (full-text search), `tagulous` (tags), `auditlog` + `pghistory` + `pgtrigger` (two parallel audit trails), `rest_framework` + `drf_spectacular` (API + OpenAPI), `dbbackup`, `django_celery_results`, `single_session`. There is no app-per-domain split — `dojo/models.py` is 4 974 lines and holds essentially every model.

Celery is wired in `dojo/celery.py`. Notably it overrides `Task` with a stack of three custom base classes (`DojoAsyncTask` → `PluggableContextTask` → `PgHistoryTask`, `dojo/celery.py:15-140`) that inject the dispatching user's id into every task's kwargs and re-apply `crum.impersonate` + `pghistory.context` inside the worker, so audit attribution survives across the queue. Dispatch helpers live in `dojo/celery_dispatch.py:40-80` (`dojo_create_signature`, `dojo_dispatch_task`). A user-level `block_execution` flag forces synchronous execution per user (`dojo/decorators.py:58-82`). Beat schedule is in `dojo/settings/settings.dist.py:872-946` and covers alerts, dedupe cleanup, audit-log flush, JIRA reconciliation, SLA notify, risk-acceptance expiry, webhook health, session cleanup.

There are 41 management commands under `dojo/management/commands/` — data migrations (`migrate_authorization_v2.py`, `migrate_endpoints_to_locations.py`, `migrate_cve.py`, `jira_refactor_data_migration.py`), maintenance (`fix_loop_duplicates.py`, `fix_broken_endpoint_status.py`, `dedupe.py`, `dupecheck.py`, `flush_auditlog.py`), bootstrap (`initialize_permissions.py`, `initialize_test_types.py`, `complete_initialization.py`), and import drivers (`import_all_unittest_scans.py`, `import_unittest_scan.py`).

## 2. Module / package layout

The codebase is partially mid-refactor: there is an old "everything in `dojo/{models,forms,filters}.py` plus a `dojo/api_v2/`" shape, and a new per-domain shape (`models.py`/`services.py`/`queries.py`/`ui/`/`api/`) only fully realized in two modules (`dojo/url/`, `dojo/location/`). What you actually find:

- `dojo/api_v2/` (8 330 LOC total) — `serializers.py` 3 387 LOC, `views.py` 3 668 LOC, `permissions.py` 1 287 LOC, plus `prefetch/` (DRF prefetch mixin + custom OpenAPI schema gen, `dojo/api_v2/prefetch/prefetcher.py`).
- `dojo/tools/` — 221 subpackages, one per scanner; covered in §3.
- `dojo/importers/` — orchestration layer that sits between a parser and the DB (`base_importer.py`, `default_importer.py`, `default_reimporter.py`, `auto_create_context.py`, `endpoint_manager.py`, `base_location_manager.py`, `options.py`).
- `dojo/finding/` — has the dedupe engine (`deduplication.py`), import helpers (`helper.py`), queries, urls, views. Model itself still lives in `dojo/models.py:2397`.
- `dojo/engagement/`, `dojo/product/`, `dojo/endpoint/`, `dojo/metrics/`, `dojo/notifications/` — domain modules with `services.py` / `queries.py` / `views.py`.
- `dojo/jira/` — see §6. 3 917 LOC, fully self-contained module.
- `dojo/github/` — smaller GitHub integration counterpart.
- `dojo/authorization/` — see §9.
- `dojo/auditlog/services.py` — programmatic `pghistory.track()` registration (≥10 invocations, `dojo/auditlog/services.py:174-301`).
- `dojo/location/` — newer abstraction replacing endpoints, see `V3_FEATURE_LOCATIONS` flag.

## 3. Importer / parser architecture

This is the centerpiece. **221 scanner integrations** under `dojo/tools/<scanner>/parser.py` register themselves via **convention discovery**, not a static table.

The discovery loop is `dojo/tools/factory.py:108-128`:

```python
for module_name in os.listdir(package_dir):
    if find_spec(f"dojo.tools.{module_name}.parser"):
        module = import_module(f"dojo.tools.{module_name}.parser")
        for attribute_name in dir(module):
            expected_base = module_name.replace("_", "") + "parser"
            if isclass(attribute) and (
                attribute_name.lower() == expected_base or
                re.match(rf"^{re.escape(expected_base)}v\d+$", attribute_name.lower())):
                register(attribute)
```

So `dojo/tools/trivy/parser.py` must expose a class whose name lowercases to `trivyparser` (or `trivyparserv2`). `register()` (line 16-21) calls `parser_type().get_scan_types()` and inserts every returned label into the module-global `PARSERS` dict (`dojo/tools/factory.py:11`). `get_parser(scan_type)` (line 33) is the dispatch — it also lazily inserts a `Test_Type` row, so test types are bootstrapped from code at first use (line 40). The `" detailed"` suffix flips the parser into a `set_mode("detailed")` mode used by Checkmarx/SonarQube/Anchore variants (line 19-20).

The per-parser contract is duck-typed:

- `get_scan_types() -> list[str]` (e.g. `["Trivy Scan"]` at `dojo/tools/trivy/parser.py:58`).
- `get_label_for_scan_types(scan_type)` and `get_description_for_scan_types(scan_type)`.
- `get_findings(scan_file, test) -> list[Finding]` — returns unsaved `Finding` instances with `unsaved_endpoints`, `unsaved_locations`, `unsaved_vulnerability_ids`, `unsaved_tags`, `unsaved_req_resp`, `unsaved_files`.
- Optional `requires_file(scan_type)`, `requires_tool_type(scan_type)`, `api_scan_configuration_hint()` for API-importing parsers (`dojo/tools/factory.py:69-105`).
- Optional `get_fields()` / `get_dedupe_fields()` purely for documentation (e.g. `dojo/tools/burp/parser.py:24-79`).

Three illustrative shapes:

- **Trivy** (`dojo/tools/trivy/parser.py`) — pure JSON parser. Handles three schema variants in one method: legacy list, `SchemaVersion == 2`, and Kubernetes "ClusterName" schema (lines 168-199). Includes a 70-line VEX status mapping table (`convert_trivy_status`, lines 81-158) that translates Trivy's `not_affected`/`under_investigation`/`will_not_fix`/... into DefectDojo's `(active, verified, is_mitigated)` triple.
- **Tenable** (`dojo/tools/tenable/parser.py`) — thin dispatcher that routes to either `TenableCSVParser` or `TenableXMLParser` based on file content. The directory holds `csv_format.py`, `xml_format.py`, `utils.py`. (No `nessus/` directory exists; "Nessus" is folded into the Tenable parser.)
- **Burp** (`dojo/tools/burp/parser.py`) — XML via `defusedxml.ElementTree`, decodes base64 request/response (`get_clean_base64`, lines 136-152), folds duplicate `vuln_id_from_tool` entries by merging `unsaved_endpoints`/`unsaved_locations`/`unsaved_req_resp` into a single finding inside the parser (lines 97-123) — intra-file dedupe before the global dedupe pass.

The importer that consumes a parser's output is `dojo/importers/default_importer.py:165-260`. It (1) sanitizes severities and drops below-threshold findings, (2) sets `test`, `reporter`, override active/verified, (3) calls `finding.set_hash_code(True)` BEFORE save, (4) calls `finding.save_no_options()`, (5) processes locations/files/vuln_ids in a separate pass, (6) accumulates a 1 000-finding batch and dispatches `post_process_findings_batch` (`dojo/finding/helper.py:459`) as a Celery task per batch. Reimport goes through `dojo/importers/default_reimporter.py:261`, with `process_findings` returning matched-vs-new buckets and closing missing-on-reimport findings.

## 4. Finding deduplication

Configuration lives entirely in `dojo/settings/settings.dist.py`:

- `HASHCODE_FIELDS_PER_SCANNER`: ~100-entry dict, scan-type → list of fields used to compute the SHA-256 (`dojo/settings/settings.dist.py:978-1097`). Example: `"Trivy Scan": ["title", "severity", "vulnerability_ids", "cwe", "description"]`, `"Burp Scan": ["title", "severity", "vuln_id_from_tool"]`.
- `HASHCODE_ALLOWED_FIELDS` whitelist (`dojo/settings/settings.dist.py:1176`) — `title, cwe, vulnerability_ids, line, file_path, payload, component_name, component_version, description, endpoints, unique_id_from_tool, severity, vuln_id_from_tool, mitigation`. `endpoints` is a pseudo-field that resolves to `Location` rows when `V3_FEATURE_LOCATIONS` is on.
- `HASH_CODE_FIELDS_ALWAYS = ["service"]` (`dojo/settings/settings.dist.py:1179`) — appended to every hash.
- `HASHCODE_ALLOWS_NULL_CWE` per-scanner override (`dojo/settings/settings.dist.py:1120-1171`). Falls back to legacy when CWE=0 and the scanner isn't whitelisted.
- `DEDUPLICATION_ALGORITHM_PER_PARSER` (`dojo/settings/settings.dist.py:1218-1297`) — picks one of `legacy`, `unique_id_from_tool`, `hash_code`, `unique_id_from_tool_or_hash_code` per scan type.
- Entire config can be overridden at boot by env var `DD_HASHCODE_FIELDS_PER_SCANNER` (JSON merge at `dojo/settings/settings.dist.py:1100-1114`).

Hash computation: `Finding.compute_hash_code` (`dojo/models.py:3029-3090`). Builds a concatenation of stringified field values in `HASHCODE_FIELDS_PER_SCANNER` order, with special handling for `endpoints` (calls `get_locations()`) and `vulnerability_ids` (calls `get_vulnerability_ids()`, which falls back from saved `Vulnerability_Id` rows to `unsaved_vulnerability_ids` before save, lines 3098-3120). `hash_fields` (line 3181) appends `HASH_CODE_FIELDS_ALWAYS` and returns `sha256(s.casefold().encode().strip()).hexdigest()` — **lower-cased, NOT length-prefixed**, so ordering of fields matters and collisions between field-value boundaries are possible. The legacy algorithm is hardcoded: `title + cwe + line + file_path + description` (`dojo/models.py:3092-3095`). Saving a Finding calls `compute_hash_code()` (line 3656).

A custom `FINDING_COMPUTE_HASH_METHOD` hook (line 3032) lets DefectDojo Pro replace the algorithm without forking.

Dedupe execution: `dojo/finding/deduplication.py`. `do_dedupe_finding_task_internal` (line 70) is the single entry. Algorithm dispatch is on `test.deduplication_algorithm` (a `@property` at `dojo/models.py:2261-2275` that consults `DEDUPLICATION_ALGORITHM_PER_PARSER`). Four matchers:

- `_dedupe_batch_hash_code` via `find_candidates_for_deduplication_hash` (line 372) — single `hash_code__in` query scoped to the same Product or Engagement (governed by `Engagement.deduplication_on_engagement`, `dojo/models.py:1583`).
- `_dedupe_batch_unique_id` — same shape but on `unique_id_from_tool`, scoped to `test__test_type=test.test_type` because `unique_id_from_tool` is parser-specific (line 422).
- `_dedupe_batch_uid_or_hash` — combined OR query (line 433-475).
- `_dedupe_batch_legacy` (line 478) — Q-OR by title/cwe, then in-Python comparison.

Per-finding processing reuses prefetched candidate maps (`get_finding_models_for_deduplication` at line 17 selects only `DEDUPLICATION_FIELDS` listed on the Finding model at `dojo/models.py:2403-2430`, deferring heavyweight text columns listed at lines 2435-2445). Cleanup of excess duplicates is a separate beat task (`dojo/tasks.py:36-103`, scheduled every minute at `settings.dist.py:887-893`) that respects `System_Settings.max_dupes` and `DUPE_DELETE_MAX_PER_RUN`.

## 5. Engagement / Product / Test hierarchy

Five-level hierarchy: `Product_Type → Product → Engagement → Test → Finding`. All in `dojo/models.py`:

- `Product_Type` at line 839, `Product` at 1128 (FK `prod_type`), `Engagement` at 1535 (FK `product`, `on_delete=CASCADE`), `Test` at 2163 (FK `engagement`, FK `test_type` → `Test_Type` at line 923), `Finding` at 2397 (FK `test`).
- `Engagement` is the only place where dedupe scope can be narrowed: `deduplication_on_engagement = BooleanField(default=False)` (`dojo/models.py:1583`); when `False`, dedupe is product-wide.
- `Engagement` carries CI/CD metadata (`build_id`, `commit_hash`, `branch_tag`, `build_server` / `source_code_management_server` / `orchestration_engine` FKs to `Tool_Configuration`, lines 1573-1582). `Test` mirrors `build_id`/`commit_hash`/`branch_tag` (lines 2188-2193) so reimports can update them per-scan.
- Group memberships and roles are first-class: `Product_Member`, `Product_Group`, `Product_Type_Member`, `Product_Type_Group` (1392-1407), all carrying a `role` FK that gates permissions (§9).
- `Engagement` has `Meta.indexes = [Index(fields=["product", "active"])]` (line 1591); `Test` has `Index(fields=["engagement", "test_type"])` (line 2198). Notable absence: there is no DB-level uniqueness on `Test_Type.name` despite `factory.get_parser` doing `get_or_create(name=scan_type)` on every parser dispatch (`dojo/tools/factory.py:40`).

Import requires a `Test`. When the API caller omits one, `AutoCreateContextManager` (`dojo/importers/auto_create_context.py:25-192`) walks the chain top-down, looking up by name (`product_type_name`, `product_name`, `engagement_name`), creating missing nodes. There is an explicit guard at line 143-149 that refuses if a found Product's `prod_type.name` doesn't match the supplied `product_type_name`, preventing accidental cross-tenant import.

## 6. JIRA integration

Self-contained module `dojo/jira/` (3 917 LOC, of which `helper.py` is 2 070).

Schema (`dojo/jira/models.py`): `JIRA_Instance` (line 9, holds connection URL + creds + per-severity priority strings on lines 37-41), `JIRA_Project` (line 102, attached to either a Product or an Engagement), `JIRA_Issue` (line 177, links a Dojo Finding to a Jira issue key).

Priority mapping is per-instance, not global. `JIRA_Instance.get_priority(severity)` (`dojo/jira/models.py:62-72`) returns one of the five `*_mapping_severity` strings. The helper `jira_priority(obj)` (`dojo/jira/helper.py:724-739`) dispatches: for a Finding it uses `obj.severity`; for a `Finding_Group` it uses `Finding.get_severity(max_number_severity)` — group priority is the worst child's priority.

Push direction (Dojo → Jira): `push_to_jira(obj, …)` (`dojo/jira/helper.py:760-778`) dispatches by type (Finding, Finding_Group, Engagement → epic) through three separate Celery tasks (`push_finding_to_jira`, `push_finding_group_to_jira`, `push_engagement_to_jira`, lines 782-822), each of which then routes to `add_jira_issue` (line 901) or `update_jira_issue` (line 1066). Field assembly is centralized in `prepare_jira_issue_fields` (line 850-898): only inserts `labels`, `environment`, `priority`, `duedate`, `epic_name_field` if they're whitelisted in the project's `issuetype_fields` — the integration is aware that custom Jira workflows have varying required fields.

Validation (`can_be_pushed_to_jira`) returns an explicit `error_code` so the caller can suppress alerts for expected refusals (`not_active_or_verified`, `below_minimum_threshold`, `empty`, `inactive`) — alerting is reserved for unexpected configuration failures (`dojo/jira/helper.py:930-952`).

Sync direction (Jira → Dojo): the webhook endpoint is `dojo/jira/views.py:54-130`. It requires `application/json`, accepts only `comment_created` and `jira:issue_updated` events (line 96), validates a `jira_webhook_secret` from system settings (lines 76-83) unless `disable_jira_webhook_secret` is set. The webhook then resolves the `JIRA_Issue` row by issue id and routes to comment/status sync. Status mapping uses two whitelists: `RESOLVED_STATUS = ["Inactive", "Mitigated", "False Positive", "Out of Scope", "Duplicate"]` and `OPEN_STATUS = ["Active", "Verified"]` (`dojo/jira/helper.py:52-63`).

Background reconciliation: `jira_status_reconciliation_task` (`dojo/tasks.py:128-138`) is wired but commented out of beat by default (`dojo/settings/settings.dist.py:937-940`); it's intended for periodic catch-up when webhooks miss events.

## 7. REST API (`api_v2/`)

DRF, namespaced at `/api/v2/`. Schema is OpenAPI 3 via `drf-spectacular`, configured at `dojo/settings/settings.dist.py:677-696`, served by `DojoSpectacularAPIView` (`dojo/api_v2/views.py:227`) which wraps the standard view with a custom JSON renderer (`DojoOpenApiJsonRenderer`, line 220) that respects an `indent` accept-parameter.

Serializers and viewsets are mostly still in two monoliths: `serializers.py` (3 387 LOC, ~120 serializer classes) and `views.py` (3 668 LOC, ~50 viewsets). Common base `DojoModelViewSet` (`views.py:231`) just adds a `DeletePreviewModelMixin`; `PrefetchDojoModelViewSet` (line 238) mixes in a custom prefetcher.

The custom prefetcher is interesting (`dojo/api_v2/prefetch/prefetcher.py`, 168 LOC, plus `schema.py` 105 LOC). It implements a `?prefetch=field,field` query parameter that returns related objects inlined in the response body — schema is described to drf-spectacular via `schema_with_prefetch()` (`views.py:272-273`). This avoids forcing clients to N+1-fetch related models.

Permissions: every domain ViewSet has its own permission class in `dojo/api_v2/permissions.py` (1 287 LOC, ~40 `UserHas*Permission` classes, e.g. `UserHasEndpointPermission:330`, `UserHasDojoMetaPermission:228`). Each implements both `has_permission` (request-level) and `has_object_permission` (per-row), delegating to `dojo.authorization.authorization.user_has_permission` (§9).

The big "/import-scan" and "/reimport-scan" endpoints invoke `DefaultImporter` / `DefaultReImporter` directly from the serializers (`serializers.py` imports both at lines 41-42), which feels backwards — the import is heavyweight and runs inside the request thread until it dispatches a Celery batch.

## 8. Background work (Celery)

Most user-visible operations run synchronously (the request thread does the work and the response carries the result). What's async:

- **Per-finding post-processing**: `post_process_finding_save` (`dojo/finding/helper.py:396`) — dedupe + rules + product grading + JIRA push. Importer skips per-finding dispatch and uses **batched** `post_process_findings_batch` (line 459) every 1 000 findings, controlled by `IMPORT_REIMPORT_DEDUPE_BATCH_SIZE` (default 1 000, `settings.dist.py:205`).
- **Dedupe**: `do_dedupe_finding_task` and `do_dedupe_batch_task` (`dojo/finding/deduplication.py:48-67`). These are decorated `@app.task` but called synchronously inside the post-process loop — the decoration is so they're available for explicit async dispatch from management commands or the UI.
- **JIRA**: `push_finding_to_jira`, `push_finding_group_to_jira`, `push_engagement_to_jira`, `close_epic`, plus a half-dozen other `@app.task`s in `dojo/jira/helper.py:782-1623`.
- **Notifications**: `dojo/notifications/tasks.py` — `add_alerts` (beat, hourly), `cleanup_alerts` (8h), `async_sla_compute_and_notify_task` (daily 07:30), `webhook_status_cleanup` (every minute), plus `webhook_reactivation` for disabled endpoints.
- **Misc beat tasks** (`dojo/settings/settings.dist.py:872-946`): `async_dupe_delete` every minute, `flush_auditlog` every 8h, `update_findings_from_source_issues` every 3h, `risk_acceptance.expiration_handler` every 3h, `clear_sessions` weekly.
- **Watson search index updates**: `update_watson_search_index_for_model` (`dojo/tasks.py:153-167`).

Per-user opt-out: `Dojo_User.block_execution` forces synchronous execution for tasks dispatched by that user (`dojo/decorators.py:73-77`) — useful for tests and for users who need deterministic UI feedback.

The user-id and pghistory context propagation through `DojoAsyncTask` (`dojo/celery.py:15-80`) means the worker rehydrates `crum.get_current_user()` and the audit trigger sees the actual originating user, not a service account.

## 9. Permissions / multi-tenancy

`dojo/authorization/` implements the object-permission model. Permissions are `IntEnum` constants in `dojo/authorization/roles_permissions.py:28-` keyed in numeric ranges by resource (1xxx = product_type, 11xx = product, 12xx = engagement, 13xx = test, 14xx = finding, 15xx = location, …). Roles are also an `IntEnum` (`Reader=5, API_Importer=1, Writer=2, Maintainer=3, Owner=4`, line 4-9). Role-to-permission mapping is `get_roles_with_permissions()`.

The core check is `user_has_permission(user, obj, permission)` (`dojo/authorization/authorization.py:75-`). Logic by type:

- `Product_Type` (line 88-101): superuser ⇒ allow; otherwise look up `Product_Type_Member` and `Product_Type_Group` rows and check `role_has_permission`.
- `Product` (line 102-): inherits from its `prod_type` first, then falls back to `Product_Member` / `Product_Group`.
- Engagement/Test/Finding/Endpoint/Risk_Acceptance: resolve the parent Product and delegate.
- Global roles short-circuit anything at the Product_Type level (line 84-86), via `user_has_global_permission`.

`user_has_permission_or_403` (line 285) raises `PermissionDenied` for use in views. All UI views use `@user_is_authorized` decorators from `dojo/authorization/authorization_decorators.py`; API viewsets use the parallel `permissions.UserHas*Permission` DRF classes (§7). The check is wrapped in `@cache_for_request` (line 33), which memoizes per request via `dojo/request_cache/`.

Multi-tenancy is enforced **not at the connection level** (one DB serves all) but at every query: `dojo/finding/queries.py`, `dojo/engagement/queries.py`, `dojo/product/queries.py`, etc. each export `get_authorized_<model>(permission)` helpers that build `.filter(Q(prod_type__members__user=...) | Q(...))` querysets. ViewSets always start with these (e.g. `EngagementViewSet.get_queryset` calls `get_authorized_engagements`). **There is no row-level DB enforcement** — every leak risk is at the query-helper boundary.

## 10. What's novel at the code level

- **Parser registry by directory convention, not enumeration.** Adding a scanner is "drop `dojo/tools/<name>/parser.py` with a class named `<Name>Parser` exposing `get_scan_types()`" — no manifest, no `__init__.py` edits, no migration. The dispatch table (`dojo/tools/factory.py:11`) is built at import time, and `Test_Type` rows are conjured on first parser use (line 40). This makes the long tail of 221 integrations sustainable.
- **Per-scanner hash configuration as data, not code.** `HASHCODE_FIELDS_PER_SCANNER` in `settings.dist.py` is a single ~100-entry dict that operators can override via one env var (`DD_HASHCODE_FIELDS_PER_SCANNER` as JSON). Combined with `DEDUPLICATION_ALGORITHM_PER_PARSER`, the entire dedupe semantics for a deployment are settings-driven and tuneable per parser without code changes — a security tooling rarity.
- **Custom Celery `Task` base classes propagate user identity and pghistory context across the queue boundary.** `DojoAsyncTask.apply_async` injects `async_user_id` and `_pgh_context` into every dispatch (`dojo/celery.py:54-80`); the worker pops them and re-enters `crum.impersonate` + `pghistory.context` before running. The result: an audit row created by a 5-minute-later background task is attributed to the user who clicked the button, not to the worker. Most Django+Celery apps lose this attribution.

Caveats: the README's "200+ scanners" claim matches reality (221 directories under `dojo/tools/`). The CLAUDE.md in the submodule describes an in-progress reorganization (per-domain `models.py`/`services.py`/`ui/`/`api/`); on disk, only `dojo/url/` and `dojo/location/` are fully reshaped — `dojo/jira/`, `dojo/notifications/`, `dojo/github/`, `dojo/engagement/`, `dojo/finding/` are partial. `dojo/models.py` remains a 4 974-line monolith.
