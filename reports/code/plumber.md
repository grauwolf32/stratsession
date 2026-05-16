# Plumber — code-level analysis

Code base: `sources/ci-cd/plumber/` (Go module `github.com/getplumber/plumber`, OPA-backed CI/CD compliance scanner). Line numbers refer to the working tree.

## Architecture overview

Entry point is a four-line `main.go:1-7` that just calls `cmd.Execute()`. The CLI is built with Cobra; `cmd/root.go:19-31` declares the root command. `Execute()` distinguishes a `ComplianceError` (exit 1) from any other error (exit 2) via `errors.As` at `cmd/root.go:51-57`. A non-blocking `PersistentPreRunE` goroutine kicks off an update check (`cmd/root.go:24-30`).

Subcommands registered into `rootCmd` live in `cmd/`: `analyze.go`, `analyze_github.go`, `config.go` / `config_migrate.go` / `init.go`, `explain.go`, `render_details.go`, `legacy_json*.go`, `update_check.go`, `version.go`. The orchestration pipeline:

1. Provider detection from git remote via `utils.DetectGitRemote()` at `cmd/analyze.go:194`, with explicit flag overrides. GitHub remotes dispatch to `runGitHubAnalyze` (`cmd/analyze.go:208-210`); GitLab continues through `control.RunAnalysis(conf)` (`cmd/analyze.go:321`).
2. Provider-specific collectors hit APIs / local files and emit `*ir.NormalizedPipeline`.
3. The OPA engine evaluates every embedded `.rego` policy against that IR and returns `[]opaengine.Finding` (`internal/engine/opa/engine.go:177-205`).
4. Findings are filtered by `.plumber.yaml` enabled-controls + `--controls/--skip-controls` (`control/task.go:127`), then rendered to stdout / JSON / PBOM / CycloneDX / MR comment / project badge (`cmd/analyze.go:374-458`).

## Module / package layout

- `cmd/` — Cobra commands, flag parsing, terminal rendering (Lipgloss tables, `cmd/spinner.go`). `cmd/legacy_json*.go` reproduces the v0.2.x JSON shape for back-compat.
- `collector/` — provider data acquisition. `dataCollectionGitlabPipeline{Origin,Image}.go` and `dataCollectionGitlabProtection.go` call the GitLab APIs; `github_workflows.go`, `github_workflows_remote.go`, `github_metadata.go`, `github_branch_protection.go`, `github_repo_artifacts.go` are the GitHub side. `gitlab_ir.go` + `github_workflows.go` map raw provider data to the IR.
- `control/` — orchestration on top of the OPA engine. `task.go` / `task_github.go` host `RunAnalysis` / `RunGitHubAnalysis`; `catalog.go` enumerates the 14 GitLab + 9 GitHub controls; `codes.go` maps ISSUE codes back to controls; `scoring.go` computes the letter score; `bench_filter.go` honours per-file bench markers; `mrcomment.go`, `badge.go`, `github_stats.go` are output integrations.
- `gitlab/` — REST + GraphQL client (`client.go`, `rest.go`, `request.go`), retry transport (`retry.go`), models, MR + badge calls, CI-env helpers (`utilsCI.go`).
- `internal/engine/opa/engine.go` — the OPA wrapper (only place importing `github.com/open-policy-agent/opa/v1/rego`).
- `internal/ir/pipeline.go` — single source of truth for the provider-agnostic IR types.
- `internal/defaultconfig/embed.go` — embeds `default.yaml` for the bundled `.plumber.yaml` fallback.
- `policies/` — 60+ `.rego` files + `embed.go` (`//go:embed *.rego`).
- `pbom/` — `generate.go`, `generate_github.go`, `cyclonedx.go`, `types.go`.
- `templates/plumber.yml` — published GitLab CI Component spec/inputs.
- `configuration/` — `.plumber.yaml` schema + loader + v1→v2 migration.

## Provider-agnostic IR design

The IR is the load-bearing abstraction. `internal/ir/pipeline.go:17-67` defines `NormalizedPipeline{Provider, ProjectPath, DefaultBranch, Jobs, Includes, Branches, Dependabot, Dockerfiles, GlobalVariables, LocalGlobalVariables, RenovateConfigPath, SecurityPolicyPath, Raw}`. `Provider` is the `gitlab` / `github` discriminator (`pipeline.go:7-13`). The package doc states the contract: "Provider collectors produce an `*ir.NormalizedPipeline` that the OPA rule engine consumes regardless of the source."

Two normalizers in `collector/`:

- GitLab: `collector.ToNormalizedPipeline(...)` at `collector/gitlab_ir.go:30-60` takes the three GitLab collector outputs and builds the IR. It is pure (no I/O) — `gitlab_ir.go:27-29` explicitly documents this so tests can pass synthetic fixtures.
- GitHub: `collector.ScanGitHubWorkflows(...)` at `collector/github_workflows.go:28-84` walks `.github/workflows/*.yml`, parses each file, namespaces job names with the workflow base name to avoid collisions, then enriches via `enrichActionsWithAPIMetadata` (line 80-82). The remote-fetch variant is `collector/github_workflows_remote.go`. The 0.3.0-beta GitHub support shares the same struct — only new fields were added (`Job.Permissions`, `Job.Triggers`, `Job.Uses`, `Job.ReusableWorkflowUses`, `Job.SecretsInherit`, `Job.Conditions`, `Job.WorkflowHasConcurrency` at `pipeline.go:154-208`).

Provider asymmetry is encoded on the IR itself. `Branch.ProtectionDetailsKnown` at `pipeline.go:316-325` exists so a Rego rule checking `codeOwnerApprovalRequired` does not false-positive against a read-only GitHub token (where the protection endpoint 403s). The GitLab normalizer hard-codes `ProtectionDetailsKnown=true` at `collector/gitlab_ir.go:77` because GitLab returns the detail in the listing payload.

The same Rego policy reasons over both providers because both normalizers project onto identical `ir.Job` and `ir.Branch` shapes. `image_mutable_tag.rego` walks `input.pipeline.jobs[i].image.tag` provider-blind. Provider-specific concerns (action pinning, `permissions: write-all`, dangerous triggers) live in policies that read GitHub-only fields; GitLab jobs leave those zero-valued and the rules emit nothing.

## Rego policy engine integration

OPA library: `github.com/open-policy-agent/opa/v1/rego`, imported only at `internal/engine/opa/engine.go:21`. The engine type is `Engine{modules map[string]string}` (`engine.go:115-117`). Loading: `engine.LoadFromFSFiltered(policies.FS, skip)` at `control/task.go:117`; the `skip` predicate consults `IsRegoFileBenchedForProvider` so dev-side benched policies never load. Module logical names are the file basename without extension (`engine.go:165`); the engine queries `data.<name>.deny` (`engine.go:304`).

Evaluation is one `rego.New(...).Eval(ctx)` per loaded module (`engine.go:302-323`), iterated in sorted module-name order at `engine.go:187-201`. Each policy sees a JSON round-tripped input of `{pipeline, config}` at `engine.go:287-300`. `config` is the result of `buildEngineConfig(controls)` (`control/task.go:139-272`), which projects relevant `.plumber.yaml` sections into a Rego-friendly map (e.g. `input.config.imageMutableTag.forbiddenTags`). Findings come out of `rs[0].Expressions[0].Value`, JSON-marshalled and unmarshalled into `[]Finding`. `enrichFindingsWithJobLocation` (`engine.go:247-282`) backfills `File`/`Line` from `pipeline.Jobs[].OriginFile/OriginLine` when the rule did not set one and stamps `docUrl = https://getplumber.io/docs/use-plumber/issues/<code>` on every finding (`engine.go:239`). Findings are sorted deterministically (`engine.go:212-222`) and `Finding.MarshalJSON` (`engine.go:50-74`) flattens `Data` into top-level keys for back-compat with pre-Rego consumers.

## The 14 GitLab + 9 GitHub controls

Canonical lists in `control/catalog.go`: `GitLabControls(pc)` at `catalog.go:41-125` returns 14 `ControlEntry` records; `GitHubControls(pc)` at `catalog.go:134-197` returns 9. Each entry is `{DisplayName, ControlName, Skipped, Compliance}`. The ISSUE-code → control mapping is in `control/codes.go`; `FilterFindingsByEnabledControls` drops findings whose owning control was not enabled in `.plumber.yaml`.

Policies live as flat files at `policies/*.rego` (60+ files; the directory currently mixes the shipped 14 + 9 with benched, experimental and GHA-port rules). `policies/embed.go:1-13` notes the planned subdirectory split has not landed. Three illustrative examples:

- `policies/image_mutable_tag.rego:14-28` — GitLab `containerImageMustNotUseForbiddenTags`. Walks `input.pipeline.jobs[i].image.tag`, uses `glob.match(pattern, null, tag)` against `input.config.imageMutableTag.forbiddenTags`, emits `ISSUE-102` (high).
- `policies/excessive_permissions.rego:13-23` — GHA-only check on `job.permissions == "write-all"`, emits `ISSUE-509` (high). Reads a field the GitLab collector never populates, so it's implicitly a no-op on GitLab pipelines.
- `policies/branch_unprotected.rego:10-33` — provider-agnostic. Walks `input.pipeline.branches`; `_branch_must_be_protected` matches against `input.config.branchMustBeProtected.namePatterns` and (when `defaultMustBeProtected` is on) `input.pipeline.defaultBranch`. Emits `ISSUE-501` (critical).

`policies/known_vulnerable_action.rego:26-39` is notable because it reads collector-resolved API metadata (`action.metadata.advisories`) rather than raw workflow text — showing the IR's role as carrier of API-derived facts to the policy layer.

## PBOM + CycloneDX emission

`pbom/types.go:22-34` defines `PBOM{PBOMVersion, GeneratedAt, Project, Summary, PlumberScore, ContainerImages, Includes}`. `pbom.Version = "1.0.0"` (`types.go:16`). Data model is intentionally narrow: container images (`ContainerImage{Image, Registry, Name, Tag, Jobs, Authorized, ForbiddenTag}` at `types.go:71-86`) and pipeline includes (`Include{Type, Location, Project, Version, LatestVersion, UpToDate, ComponentName, FromCatalog, Nested, Overridden, OverriddenJobs}` at `types.go:88-119`). `Type` discriminator covers `component / project / local / remote / template` (GitLab) and `action / reusableWorkflow` (GitHub).

`pbom.NewGenerator(...)` at `pbom/generate.go:38-45` is built per analysis; `WithComplianceData` (`generate.go:48-51`) attaches image-compliance booleans so `Authorized` and `ForbiddenTag` are filled in from the corresponding control's findings. `Generate(...)` at `generate.go:60-93` builds the PBOM; `generate_github.go` is the GitHub counterpart.

CycloneDX: `(*PBOM).ToCycloneDX(plumberVersion)` at `pbom/cyclonedx.go:60`, spec 1.5 (`cyclonedx.go:12`). Output uses `urn:uuid:` serial numbers via `github.com/google/uuid`, declares Plumber as the `tools` entry, emits the project as the main `application` component, and flattens PBOM images / includes into `components[]`.

## GitLab + GitHub API client implementation

GitLab: `gitlab.GetNewGitlabClient(token, instanceUrl, conf)` at `gitlab/client.go:21-56` switches between `gitlab.NewClient` (when token has prefix `glpat-`) and `gitlab.NewOAuthClient` otherwise, using `gitlab.com/gitlab-org/api/client-go`. GraphQL uses `machinebox/graphql` (`gitlab/client.go:59-80`). Auth + PAT scope handling is external: `cmd/analyze.go:249-252` requires `GITLAB_TOKEN`; scope requirements (`read_api + read_repository`, or `api` for MR comment) live in docs/template, not code. Sensitive-log masking in `gitlab/client.go:97-109` (`glpat-`, `glcbt-`, `Authorization:` headers).

Retry / rate limit: every HTTP client wraps its transport with `WrapTransportWithRetry` (`gitlab/retry.go:208-222`). `retryableTransport.RoundTrip` (`retry.go:53-145`) retries on network errors, 429, and 5xx (`shouldRetry` at `retry.go:148-168`); exponential backoff with ±25% jitter (`calculateBackoff` at `retry.go:171-185`); body buffered for re-issue. On exhausted 429s it synthesises a JSON error body for a stable caller-side shape (`retry.go:131-142`). Pagination is delegated to the upstream SDK (no first-party paginator located).

GitHub: `collector.GitHubMetadataClient` (`collector/github_metadata.go:64-82`) wraps `github.com/cli/go-gh/v2/pkg/api`, reusing the installed `gh` CLI's credential store. Auth precedence is `GH_TOKEN > GITHUB_TOKEN > GH_ENTERPRISE_TOKEN > gh CLI`, mirrored in `cmd/analyze_github.go:201-218` (`detectGitHubAuthSource`) so the pre-flight banner names the source.

The "soft-degrade" mode for GitHub local-clone scans is implemented in `collector/github_metadata.go:107-143` (`NewGitHubMetadataClientForHost`). If `PLUMBER_DISABLE_GITHUB_API=1` (`github_metadata.go:19, 125-128`) or `api.DefaultRESTClient()` fails (`github_metadata.go:136-140`), `disabled=true` and `Available()` returns false. `Resolve(...)` at `github_metadata.go:154-157` short-circuits to a zero `GitHubMetadata` when disabled. Policies treat zero-value metadata as "unknown" and stay silent — the contract is documented at `github_metadata.go:36-50`. Pre-flight UX at `cmd/analyze_github.go:179-195`: local-clone with no token prints `GitHub auth: none — running in degraded mode (workflow-content controls only).` and continues; upstream-fetch path returns `ErrAuthRequired` outright (`cmd/analyze_github.go:160-162`). All caches in `GitHubMetadataClient` are mutex-protected for concurrent action enrichment.

## Integration surfaces

CLI commands (registered in `cmd/`): `analyze`, `config` (+ `config generate`, `config init`, `config migrate`), `explain`, `init`, `version`. `analyze` flag surface documented in `cmd/analyze.go:108-137`.

GitLab CI Component: `templates/plumber.yml:1-244`. Declares typed `inputs` (`gitlab_token`, `project_path`, `branch`, `server_url`, `config_file`, `threshold`, etc.) and a single `plumber` job (`templates/plumber.yml:137-244`) that runs the binary using a digest-pinned image (`templates/plumber.yml:60`) and uploads `output_file`, `pbom_file`, `pbom_cyclonedx_file` as artifacts. The CycloneDX file is registered under `reports.cyclonedx` (`templates/plumber.yml:235-237`) so GitLab's dependency-list UI picks it up natively.

MR comment: `control.ManageMergeRequestComment` (`control/mrcomment.go:21-80+`) lists notes via `gitlab.ListMergeRequestNotes`, finds the existing Plumber comment via invisible HTML marker `<!-- Plumber Compliance Comment -->` (`mrcomment.go:14-15`), and updates in place. MR detection via CI env vars in `gitlab/utilsCI.go` (`DetectMergeRequestIID`, `IsOnDefaultBranchCI`).

Project badge: `control.ManageProjectBadge` (`control/badge.go`) + `gitlab/badge.go`. Badge updates gated to default-branch CI runs (`cmd/analyze.go:419-458`); local runs against local CI files are skipped to avoid clobbering the prod badge.

Output formats: terminal (Lipgloss), JSON, PBOM (JSON), PBOM (CycloneDX 1.5). **No SARIF output is emitted** (grep for `sarif`/`SARIF` across `cmd/`, `control/`, `pbom/` returned no matches). Exit code is ternary: 0 = compliance ≥ threshold, 1 = `ComplianceError`, 2 = runtime/config error (`cmd/analyze.go:81-85`, `cmd/root.go:51-57`).

## What is genuinely novel at the code level

The provider-agnostic IR (`internal/ir/pipeline.go`) plus a single OPA evaluation loop (`internal/engine/opa/engine.go:177-205`) lets one Rego rule reason about both GitLab `include:` and GitHub Actions `uses:` semantics where they overlap, while provider-specific rules read provider-specific IR fields — the asymmetry is encoded on the IR (e.g. `Branch.ProtectionDetailsKnown`), not in the rule. The other genuinely interesting pattern is the "positive-evidence" degraded mode: `GitHubMetadataClient` returns zero-valued metadata on auth failure (`collector/github_metadata.go:154-176`), and every metadata-dependent policy is written to fire only on positive evidence, so a missing token quietly silences API-dependent rules instead of failing the run.
