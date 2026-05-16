# Sunshine — code-level analysis

## 1. Architecture overview

Sunshine is a **dual-mode application** packaged in three files (plus a single Python dependency):

```
sunshine.py    2421 lines  # CLI + Pyodide-callable library
index.html     1254 lines  # browser front-end
requirements.txt          # only "requests"
```

Mode is selected by Python's `__name__`: the CLI entry point uses `if __name__ == "__main__"` (`sunshine.py:2303`), while the browser bridge uses the non-standard sentinel `if __name__ == "__web__"` (`sunshine.py:2402`), which is set explicitly by JavaScript via `pyodideInstance.globals.set("__name__", "__web__")` (`index.html:1031`). `requests` is only imported in the CLI path (`sunshine.py:29-30`); in `__web__` mode the script imports `js.writeToLog` and `js.fetchDataSync` (`sunshine.py:33-34`).

Front-end stack is **not** D3 or React. It is plain JavaScript plus **Apache ECharts 5.5.1** (`index.html:22`) for the visualisation, jQuery 3.7.1 + DataTables 1.13.7 + Bootstrap 5.3.2 for tables and styling, plus **Pyodide 0.27.7** (`index.html:7`) to run the same `sunshine.py` in the browser, and `lzma@2.3.2` (`index.html:222`) for permalink compression. There is no build tool, no bundler, no package.json — everything is CDN-loaded.

## 2. Module / file layout

The entire backend is one file. Logical sections inside `sunshine.py`:

- `sunshine.py:86-722` — `HTML_TEMPLATE`, a ~600-line embedded HTML string with placeholders like `<CHART_DATA_HERE>`, `<COMPONENTS_TABLE_HERE>`, `<METADATA_TABLE_HERE>` used by `main_cli` for the standalone-HTML output mode.
- `sunshine.py:725-735` — `custom_print` wrapper that pivots between `print` and the JS-injected `writeToLog`, capped at `REMAINING_WEB_LOGS = 200` lines (`sunshine.py:83`).
- `sunshine.py:744-1091` — component / bom-ref normalisation.
- `sunshine.py:1108-1204` — `parse_metadata` (spec version, tools, main component).
- `sunshine.py:1260-1423` — `parse_json_data` / `parse_file` / `parse_string` ingestion entry points.
- `sunshine.py:1492-1602` — `ChildrenGatherer` and `add_root_component` building the sunburst tree.
- `sunshine.py:1661-1960` — HTML table builders.
- `sunshine.py:2192-2300` — `main_cli` and `main_web`.

The two `sample_*.html` files at the repo root are pre-rendered example outputs, not assets.

## 3. CDX parsing

CycloneDX 1.x ingestion is **JSON-only**: `parse_file` uses `json.load` (`sunshine.py:1418-1422`) with a UTF-8 errors-replace fallback; there is no XML, no Protobuf, and no SPDX path (a grep for `xml`/`spdx` in `sunshine.py` returns only the SPDX-License-Identifier comment at `sunshine.py:15`). The README tells users to convert other formats via the CycloneDX Web Tool (`index.html:229`).

In-toto statements are unwrapped at `sunshine.py:1243-1257`: if `_type` starts with `https://in-toto.io/Statement/` and `predicateType` with `https://cyclonedx.org/`, the predicate is taken as the SBOM.

Dependency-graph extraction has unusual robustness logic. `get_all_bom_refs` (`sunshine.py:1051-1091`) first scans `components`, `services`, every nested `services/components`, every `dependencies[*].ref` / `dependsOn`, and finally `metadata.component.bom-ref`. When a component lacks a `bom-ref`, `get_bom_ref` (`sunshine.py:891-949`) heuristically matches by `name@version`, `name::version`, or `name:version` suffixes against all collected refs, falls back to a "version-anywhere" match, and as a last resort synthesises a fake ref from `hash(json.dumps(...))`. The same heuristic is mirrored in `normalize_bom_ref` (`sunshine.py:963-1026`) for refs cited in `dependencies` that were never declared. Unresolved refs become "fake" components via `create_fake_component` (`sunshine.py:744-755`). The graph is then walked recursively by `ChildrenGatherer.get_children` (`sunshine.py:1498-1555`) with a 100 000-segment hard cap (`SEGMENTS_THRESHOLD`, `sunshine.py:1496`) and explicit circular-dependency detection at `sunshine.py:1513`/`1536`.

Vulnerability rating selection at `parse_vulnerability_data` (`sunshine.py:811-887`) prefers `CVSSv4 > CVSSv31 > CVSSv3 > CVSSv2 > OWASP > SSVC > other` (`sunshine.py:39-45`), then within method prefers source `NVD` over vendor over `EPSS`/unknown (`sunshine.py:787-808`), and synthesises a severity from `score` if `severity` is missing.

## 4. EPSS + CISA KEV enrichment

Enrichment is opt-in (`--enrich`, `sunshine.py:2308`). Both feeds are fetched **per-CVE** from CSV chunks hosted on a contributor's own GitHub Pages, not the official FIRST/CISA endpoints:

```
https://lucacapacci.github.io/epss/data_groups/epss_scores_{year}_{first_digit}.csv
https://lucacapacci.github.io/cisa_kev/data_groups/cisa_kev_{year}_{first_digit}.csv
```

See `get_epss` (`sunshine.py:1767-1820`) and `get_cisa_kev` (`sunshine.py:1823-1874`). The CVE id is parsed by regex `^CVE-\d{4}-\d{4,}$` (`sunshine.py:1752`) and sharded by `(year, first-digit-of-id)` so each chunk is small. The chunk is held in an in-process dict cache (`epss_cache`, `cisa_kev_cache`, allocated in `parse_json_data` at `sunshine.py:1269-1270`) for the run; 404 stores `None` so the same chunk isn't re-fetched.

There is no offline mode — `requests.get` in CLI mode (`sunshine.py:1789`) or a synchronous `XMLHttpRequest` shim `fetchDataSync` in the browser (`index.html:480-485`, invoked from Python at `sunshine.py:1785, 1840`). The browser path therefore makes blocking XHRs from inside Pyodide, which only works because the chunked URLs serve CORS-friendly static files.

## 5. Visualization

The chart is an **ECharts sunburst**, not D3, not force-directed, not Sankey. Configuration is identical in both CLI and web paths:

```
series: { radius: ['15%', '100%'], type: 'sunburst', sort: undefined,
          emphasis: { focus: 'ancestor' }, data, label: { rotate: 'radial', show: false } }
```

(`sunshine.py:466-480` for the embedded template, mirrored at `index.html:551-565`). Two charts are rendered side-by-side: `chart-container-inner` (all components) and `chart-container-only-vulnerable-inner` built from a pruned graph via `get_only_vulnerable_components` (`sunshine.py:2033-2062`), toggled by `handleShowComponentsSwitchChange` (`sunshine.py:434-447`). Innermost ring is built from any node with empty `dependency_of` (`sunshine.py:1589-1594`). When the segment count exceeds 10 000, the chart is rasterised to PNG via `echartsInstance.getDataURL({type:'png', pixelRatio:2})` and the interactive instance is disposed (`sunshine.py:661-695`, `index.html:963-998`); above the build-time `SEGMENTS_THRESHOLD` of 100 000 (`sunshine.py:1496`) chart generation is skipped entirely and a warning is shown (`sunshine.py:697-714`).

There are also three DataTables tables (info, components, vulnerabilities) instantiated at `sunshine.py:526-647` and built server-side in `build_components_table_content` (`sunshine.py:1661-1748`) and `build_vulnerabilities_table_content` (`sunshine.py:1877-1960`).

## 6. License / risk overlay

Colouring is by max vulnerability severity only — there is **no license-risk overlay**. The palette is hard-coded at `sunshine.py:57-71`: `GREY` (clean), `GREEN` (info), `YELLOW` (low), `ORANGE` (medium), `RED` (high), `DARK_RED` (critical), `LIGHT_BLUE` for "transitively vulnerable only". `determine_style` (`sunshine.py:1472-1478`) picks the colour: if `max_vulnerability_severity != "clean"` it uses that severity's style, else if `has_transitive_vulnerabilities` is True it uses `TRANSITIVE_VULN_STYLE`, otherwise grey. Severity is propagated upward by `augment_components_data`'s fixed-point loop (`sunshine.py:2164-2189`) which keeps re-walking `depends_on` until `total_transitive_vulnerabilities` stops changing.

Segment **size** is not risk-weighted: `value` returned by `get_children` (`sunshine.py:1552-1554`) is simply the leaf count (or 1 for leaves and circular nodes), so the sunburst rings are area-proportional to dependency-subtree size, not CVSS.

Licenses are parsed (`parse_licenses`, `sunshine.py:1094-1105`) and rendered as plain badges in the components table (`license_badge_for_table`, `sunshine.py:1654-1658`), but they never feed into colouring or filtering.

## 7. Export

Export is handled entirely by **DataTables Buttons**: `copy / csv / excel / print` on each of the three tables (`sunshine.py:534-538`, `577-581`, `615-619`; `index.html:822-825`). `pdfmake` is loaded (`sunshine.py:100-102`, `index.html:16-17`) but is not wired to a `pdfHtml5` button in the inspected blocks — only `print` is, with custom landscape CSS injection (`sunshine.py:538-558`). Chart export to PNG only happens when the segment cap is exceeded (`sunshine.py:678-682`); there is no user-facing "Save as SVG/PNG/PDF" button for the sunburst. The standalone `output.html` written by `main_cli` (`sunshine.py:2028-2030, 2253`) is itself the primary export artefact and embeds all data inline, so it works offline.

## 8. What's genuinely novel at the code level

- **Same Python file runs as both a CLI and inside Pyodide in the browser**, switched by a custom `__name__ == "__web__"` sentinel set from JavaScript (`sunshine.py:33, 2402`; `index.html:1031`) — the browser version has zero JS reimplementation of the parsing logic.
- **State-as-URL permalinks via client-side LZMA-compressed-then-base64-of-the-SBOM in the URL fragment** (`index.html:512-514, 918-938`) with a retry loop that splits the `Uint8Array` into N parts to dodge `String.fromCharCode` argument-count limits — letting users share an analysis without any server.
- **bom-ref reconstruction heuristic** (`sunshine.py:891-1026`) that tolerates malformed SBOMs by suffix-matching `name@version` / `name::version` / `name:version` and synthesising fake refs from `hash(json.dumps(...))` rather than aborting — practical given how often real-world CycloneDX files violate the spec.
