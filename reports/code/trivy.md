# Trivy — code-level analysis

Repo root: `sources/appsec/trivy/`. Single binary, single `main.go`; `go.mod` line 109 shows `tetratelabs/wazero v1.11.0`, line 130 `modernc.org/sqlite v1.48.2` (pure-Go SQLite for RPM/Java DBs), `go.etcd.io/bbolt` for the on-disk caches.

## Architecture overview

Entry is `cmd/trivy/main.go` (52 lines): if `TRIVY_RUN_AS_PLUGIN` is set it short-circuits into `plugin.Run`; otherwise it calls `commands.Run` (`pkg/commands/run.go`). Builds are orchestrated by Mage (`magefiles/magefile.go`); the build deliberately keeps Mage free of Trivy imports.

The scan dispatch is a string-keyed map in `pkg/commands/artifact/run.go:434-446`:

```go
scans := map[TargetKind]scanFunc{
    TargetContainerImage: r.ScanImage,
    TargetFilesystem:     r.ScanFilesystem,
    TargetRootfs:         r.ScanRootfs,
    TargetRepository:     r.ScanRepository,
    TargetSBOM:           r.ScanSBOM,
    TargetVM:             r.ScanVM,
}
```

`TargetKind` is defined at `pkg/commands/artifact/run.go:50-57` (`image|fs|rootfs|repo|sbom|vm|k8s`); `k8s` is handled in `pkg/k8s/commands/`, the rest go through the same `Runner` interface (`pkg/commands/artifact/run.go:79-98`). Every target produces an `artifact.Artifact` whose `Inspect` walks files and applies analyzers; `pkg/scan/service.go:51-63` (`Service.ScanArtifact`) then hands `artifactInfo.BlobIDs` to a `Backend.Scan` (either `pkg/scan/local/service.go` or `pkg/rpc/.../remote.go`). The staging is: walker → analyzers (per file, parallel) → post-analyzers (per filesystem subtree) → applier → vuln/misconf/secret detectors.

## Module / package layout

- `pkg/fanal/` — file analyzer ("Fanal" = File ANALyzer). Contains `analyzer/` (60+ registered analyzers), `artifact/` (image / local / repo / vm / sbom artifact builders), `applier/` (layer flattener), `walker/` (fs+tar+vm walkers), `handler/` (post-blob handlers), `cache/` interop types.
- `pkg/scan/` — `local/` (in-process scan), `ospkg/` (OS vuln matcher), `langpkg/` (language vuln matcher); `service.go:24-46` defines a `Service{backend, artifact}` pair where the backend is local or RPC.
- `pkg/k8s/` — wraps the external `trivy-kubernetes` discovery library.
- `pkg/iac/` — the entire misconfig engine: providers, Rego rules, scanners per IaC file type.
- `pkg/sbom/` — `core/bom.go` (intermediate BOM), `cyclonedx/`, `spdx/`, `io/` (encode/decode).
- `pkg/dependency/parser/` — pure parsers for ~30 manifest formats organised by language (`nodejs/{npm,pnpm,yarn,bun}`, `python/{pip,poetry,uv,pylock,pipenv,packaging}`, `java/{jar,pom,gradle,sbt}`, `golang/{mod,binary,sum}`, etc.). Independent of fanal so they can be reused.
- `pkg/db/` — trivy-db client (vulnerability DB).
- `pkg/javadb/` — trivy-java-db client (Maven coordinate ↔ SHA1 lookup for fat JARs).
- `pkg/plugin/` — third-party plugin runtime; `pkg/module/` — WASM analyzer modules (wazero, `pkg/module/module.go:15-17`).
- `pkg/oci/`, `pkg/policy/`, `pkg/vex/`, `pkg/rekor/`, `pkg/attestation/` — supporting infrastructure (artifact pull, check bundles, VEX feed, Rekor transparency-log lookup, in-toto/DSSE parsing).

## Analyzer plugin system

Every analyzer is a Go package with a side-effect `init()` that calls `analyzer.RegisterAnalyzer` (instant analyzer, per-file) or `analyzer.RegisterPostAnalyzer` (operates on a virtual filesystem after the walk). The registries are package-level globals at `pkg/fanal/analyzer/analyzer.go:29-30`:

```go
analyzers     = make(map[Type]analyzer)
postAnalyzers = make(map[Type]postAnalyzerInitialize)
```

Discovery is purely by Go blank-import: `pkg/fanal/analyzer/all/import.go` pulls in every analyzer package (54 imports, lines 4-56), and `pkg/scan/local/service.go:31` blank-imports `analyzer/all` to wire them into the local backend. **There's no reflection, no plugin file, no manifest — the import graph is the registration.**

The `analyzer` interface (`pkg/fanal/analyzer/analyzer.go:75-80`) is four methods: `Type()`, `Version()` (used as a cache-key component), `Analyze(ctx, input)`, `Required(path, info)`. `Required` is a cheap path predicate used during the walk to decide whether to open the file at all (`pkg/fanal/analyzer/analyzer.go:480`).

Three concrete patterns:

**Alpine (`pkg/fanal/analyzer/os/alpine/alpine.go`)** — 56-line file, registers a zero-value struct in `init()` (line 17), `Required` returns `slices.Contains([]string{"etc/alpine-release"}, filePath)`, `Analyze` reads one line and returns `types.OS{Family: Alpine, Name: line}`. Also implements the optional `StaticPathAnalyzer` interface (line 53) which lets the walker skip a full tree traversal when the analyzer knows exactly which files it needs.

**npm (`pkg/fanal/analyzer/language/nodejs/npm/npm.go`)** — registers as a *post*-analyzer (line 26) because npm needs to walk `package-lock.json` plus `node_modules/**/package.json` together to merge lockfile dependency edges with the per-package license metadata; the actual lock-file parsing is delegated to `pkg/dependency/parser/nodejs/npm` (line 14), keeping the parser reusable for SBOM ingestion.

**Dockerfile (`pkg/fanal/analyzer/imgconf/dockerfile/dockerfile.go`)** — a `ConfigAnalyzer` (different interface registered via `RegisterConfigAnalyzer`, line 32). It synthesises a Dockerfile from the image's history layers (`imageConfigToDockerfile`, line 77) into an in-memory `mapfs` and then routes it through `misconf.NewScanner(detection.FileTypeDockerfile, ...)` — i.e. the same Rego engine that scans on-disk Dockerfiles also scans the reconstructed one. This is the link between image scanning and the IaC engine.

## trivy-db distribution

The DB itself is a separate repo (`trivy-db`); the OSS scanner only consumes it. `pkg/db/db.go:31-36` defines two defaults: `ghcr.io/aquasecurity/trivy-db:N` and the GCR mirror `mirror.gcr.io/aquasec/trivy-db:N`, where `N` is `db.SchemaVersion`. Distribution is **not** ORAS-the-library — it is plain OCI manifest + single-layer pull done with `go-containerregistry`. `pkg/oci/artifact.go:114-159` (`Artifact.Download`) fetches `image.Layers()`, asserts exactly one layer (`len(layers) != 1` check at line 130), validates `layerMediaType` against `application/vnd.aquasec.trivy.db.layer.v1.tar+gzip` (constant at `pkg/db/db.go:26`), streams the compressed layer to a tempfile and uses `go-getter` via `pkg/downloader` to extract. Failover to the mirror is in `pkg/oci/artifact.go:246-298`.

`NeedsUpdate` (`pkg/db/db.go:105-161`) reads `metadata.json` (next-update timestamp, schema version) and refuses to start if the local schema is newer than the binary's `db.SchemaVersion`. The downloaded artifact is a tarball containing `trivy.db` — a **bbolt** file, opened read-only in this process (`pkg/db/db.go:43-45` passes `WithBoltOptions(&bolt.Options{ReadOnly: true})`). The separate writable cache is `fanal.db`, also bbolt, in `pkg/cache/fs.go:23-64`. `pkg/javadb/client.go` mirrors the same shape for `trivy-java-db` (media type `application/vnd.aquasec.trivy.javadb.layer.v1.tar+gzip`), except java-db is SQLite (hence `modernc.org/sqlite` blank-imported in `cmd/trivy/main.go:15`) and used for JAR fingerprint → coordinate resolution.

## K8s scanner

`pkg/k8s/commands/cluster.go` is the orchestrator. Discovery is delegated to `trivy-kubernetes` (`pkg/k8s/commands/cluster.go:9-11` imports `trivy-kubernetes/pkg/{artifacts,k8s,trivyk8s}`). The `trivyk8s.New(cluster, opts...).ListArtifacts(ctx)` call returns `[]*artifacts.Artifact` — each carrying the workload's YAML manifest plus the list of container images and pulled credentials. Node-level data comes from `ListArtifactAndNodeInfo` (line 41), which spawns a Job inside the cluster (the "node-collector") to read kernel/kubelet config — unless `--disable-node-collector` is set.

`pkg/k8s/scanner/scanner.go:55-148` (`Scanner.Scan`) splits the discovered artifacts into "core components" (kind ending `Components`/`Cluster`) vs workload resources, then in one pass:
1. `scanMisconfigs` runs the IaC engine over the YAML manifests.
2. A parallel pipeline (line 129, `parallel.NewPipeline`) calls `runner.ScanImage` for each container image discovered, with auto-attached `imagePullSecrets`/`serviceAccount` credentials propagated from the artifact.
3. `scanK8sVulns` (line 136) maps the core-component versions (kubelet, etcd, …) to CVEs.

A notable detail at line 124-127: when using the bbolt-backed FS cache, the parallel worker count is forced to 1 to avoid the global bbolt lock — Trivy contains a code comment about this contention. The result is a single `report.Report` with three result classes (misconfig / vuln / k8s-component-vuln) keyed back to the originating resource.

## SBOM emission (CycloneDX + SPDX)

The architectural decision worth flagging: there is a single neutral intermediate, `pkg/sbom/core/bom.go` (`core.BOM`), and both formats encode *from* and decode *to* it. `pkg/sbom/io/encode.go:45-58` (`Encoder`) takes a `types.Report` and produces a `*core.BOM`; the format-specific marshalers (`pkg/sbom/cyclonedx/marshal.go:42-48` and `pkg/sbom/spdx/marshal.go`) consume that. On the decode path, `pkg/sbom/sbom.go:256-345` (`Decode`) wires the format-specific decoder so its outer struct embeds `*core.BOM` (e.g. `&cyclonedx.BOM{BOM: bom}` at line 266) — the format's `UnmarshalJSON` populates the shared BOM directly, then `sbomio.NewDecoder(bom).Decode` lifts it into Trivy's internal `types.SBOM`.

The same `Decode` table demonstrates Trivy's somewhat unusual breadth on inbound SBOMs: it handles bare CycloneDX/SPDX, in-toto-wrapped attestations (Cosign v1 legacy *and* v0.5+), and Sigstore-bundle-wrapped DSSE envelopes (lines 298-321; format constants at lines 25-54).

## `pkg/iac/`

The IaC subsystem is functionally a fork of the former Defsec/tfsec codebase, now living inside the Trivy repo. Layout:
- `pkg/iac/providers/` — one Go package per cloud/provider IR (aws, azure, google, kubernetes, dockerfile, github, …); each provider package defines structs that scanners populate from parsed manifests.
- `pkg/iac/scanners/` — one parser per source format: `terraform/`, `terraformplan/`, `cloudformation/`, `helm/`, `kubernetes/`, `dockerfile/`, `azure/` (ARM), `ansible/`. All implement a 3-method `FSScanner` interface (`pkg/iac/scanners/scanner.go:10-16`).
- `pkg/iac/rego/` — the single evaluation engine.
- `pkg/iac/rules/register.go` — generic rule registry.

The crucial point is that **rules are Rego, not Go**. `pkg/iac/rego/scanner.go:50-80` holds OPA v1 modules (`policies map[string]*ast.Module`), a compiler, and an in-memory store. Rules ship inside the embedded `trivy-checks` module — `pkg/iac/rego/embed.go:14` imports `checks "github.com/aquasecurity/trivy-checks"`, and `LoadAndRegister` (line 19, wrapped in `sync.OnceFunc`) compiles the embedded Rego, retrieves `StaticMetadata` from each module's `__rego_metadoc__` annotations (`pkg/iac/rego/metadata.go:29` shows the `AVDID` field), and registers each with the same `coreRegistry` used by Go-implemented checks. At scan time `Scanner.scanRego` (`pkg/iac/rego/scanner.go:200-257`) iterates compiled modules, filters by provider/sourceType from the metadata, and evaluates `deny`/`warn`/`violation` rules against each input. Bundled checks can also be pulled as an OCI artifact from `mirror.gcr.io/aquasec/trivy-checks` (`pkg/policy/policy.go:25-26`, media type `application/vnd.cncf.openpolicyagent.layer.v1.tar+gzip`).

This means a third party can add a misconfig rule by writing one `.rego` file with the right annotations — they never touch Go.

## Aqua plugin system

`pkg/plugin/` is a *subprocess* model, not an in-process one. A plugin is a directory with a `plugin.yaml` (`pkg/plugin/plugin.go:23-37`: `Name/Repository/Version/Summary/Description` plus a `Platforms` matrix). `Plugin.Cmd` (line 63-81) picks the right binary per `runtime.GOOS`/`GOARCH` and returns an `*exec.Cmd` whose stdin/stdout/stderr are wired to the parent's; environment is inherited verbatim (`cmd.Env = os.Environ()`, line 78). That is how `trivy-mcp` works — it is just a separately built executable that gets exec'd.

Discovery has two layers. `pkg/plugin/manager.go:60-73` (`NewManager`) roots everything under `~/.trivy/plugins`. `pkg/plugin/index.go:22` hard-codes the upstream index `https://aquasecurity.github.io/trivy-plugin-index/v1/index.yaml`; `Update` (line 36) downloads it into `index.yaml` next to the installed plugins. Installation uses the generic `pkg/downloader` (which wraps `hashicorp/go-getter`).

A *second*, internal extension mechanism: `pkg/module/module.go` loads WASM modules via wazero (line 15-17, with `wasi_snapshot_preview1` host imports) and registers them as additional analyzers — this is how custom file-format analyzers can be added without recompiling Trivy. It is distinct from `pkg/plugin/` and effectively unused outside experimental modules.

## What's genuinely novel at the code level

1. **One Rego engine for every misconfig source.** Dockerfile reconstructed from image history (`pkg/fanal/analyzer/imgconf/dockerfile/dockerfile.go:55-61`), Terraform on disk, in-cluster K8s YAML, and Helm templates all funnel through `misconf.Scanner` → `pkg/iac/rego/scanner.go`. Most competitors either bolt a separate engine per IaC type or run external binaries (`tfsec`, `checkov`, `kube-bench`); Trivy collapsed all of them onto one OPA compiler.

2. **A neutral `core.BOM` intermediate that doubles as decode target.** The trick at `pkg/sbom/sbom.go:266` of giving the format-specific struct an embedded `*core.BOM` so format `UnmarshalJSON` populates the shared model directly removes a whole class of "format-A → format-B" translation bugs and is what makes the Sigstore/in-toto wrappers cheap to add.

3. **Pure-Go everywhere there would normally be cgo.** Pure-Go bbolt for the on-disk caches (`pkg/cache/fs.go:34`), pure-Go `modernc.org/sqlite` for RPM and Java DB (`cmd/trivy/main.go:15`), and pure-Go wazero for the WASM extension runtime (`pkg/module/module.go:15-17`). With `CGO_ENABLED=0` baked into the build env (`magefiles/magefile.go:32`), the binary is fully statically linkable, which is unusual for a tool that ships its own SQLite reader, KV store, and WASM VM.
