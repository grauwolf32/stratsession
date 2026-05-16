#!/usr/bin/env python3
"""
Generate cross-cutting analytics charts over the 33 code-level analyses
under reports/code/.

Run with:
  /tmp/stratsession-viz/bin/python3 assets/landscape/generate_code_analysis.py

Outputs PNG files to assets/landscape/code-*.png. Embedded in
reports/code/_landscape.md.

The inventory is curated from reading the 33 analyses themselves; the
tuples below are the source of truth and should be updated when a
report changes meaningfully.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

OUT_DIR = Path(__file__).parent
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e5e5e5",
    "grid.linewidth": 0.5,
    "figure.dpi": 130,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

COVERAGE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "coverage", ["#ffffff", "#dff0d8", "#7fc77f", "#2e7d32"]
)


# ============================================================================
# Curated inventory of the 33 code-analyzed tools.
#
# Fields:
#   name           - report name
#   category       - one of: cicd/cloud/dfir/defense/appsec-scanner/
#                            appsec-secret/appsec-waf/appsec-fuzzer/
#                            appsec-ai/api-sec/api-discovery/perimeter-recon/
#                            perimeter-pentest/perimeter-vuln/
#                            ref-design/vuln-mgmt
#   primary_lang   - main language
#   extra_langs    - secondary languages (e.g. ["C"] for Python+C)
#   size_bucket    - small (<3k LOC) / medium (3-15k) / large (15-100k) / huge (100k+)
#   license_class  - permissive / weak-copyleft / strong-copyleft / commercial-leaning
#   storage        - sqlite / mongo / postgres / bbolt / redis / temporal /
#                    in-memory / files / none / multi
#   sandbox        - nsjail / wasm / ebpf / native / vm / none
#   distribution   - cli / library / plugin / service / web-app / desktop-app /
#                    rules-only / multi
#   patterns       - set of architectural patterns adopted (see PATTERNS below)
#   tests          - none / minimal / good / corpus
#   hygiene_flag   - free-form note, or empty
# ============================================================================

PATTERNS = [
    "MCP server",           # ships an MCP server
    "CEL / Rego policy",    # CEL or Rego expression engine
    "YAML rules / templates",  # rules/tests as YAML
    "eBPF",                 # eBPF programs
    "WASM / wasmtime",      # WASM as sandbox or runtime
    "LLM integration",      # LLM call sites in core logic
    "Plugin system",        # third-party plugins
    "Wire-format IR",       # serialised intermediate between stages
    "Kafka / msg bus",      # Kafka or similar event bus
    "tree-sitter",          # tree-sitter parsing
    "Generated code",       # codegen as part of build/runtime
    "Polyglot (3+ langs)",  # 3+ languages in repo
]

@dataclass
class Tool:
    name: str
    category: str
    primary_lang: str
    extra_langs: list[str]
    size_bucket: str
    license_class: str
    storage: str
    sandbox: str
    distribution: str
    patterns: set[str]
    tests: str
    hygiene_flag: str = ""


# Curated from reading the actual reports under reports/code/.
TOOLS: list[Tool] = [
    # ----- Round 1 (9 new 2026) -----
    Tool("SmokedMeat", "cicd", "Go", [], "large", "strong-copyleft",
         "bbolt", "none", "service",
         {"YAML rules / templates", "Plugin system"},
         "good"),
    Tool("Plumber", "cicd", "Go", [], "medium", "weak-copyleft",
         "none", "none", "cli",
         {"CEL / Rego policy", "Wire-format IR", "Plugin system"},
         "good"),
    Tool("Brutus", "perimeter-recon", "Go", ["Rust"], "medium", "permissive",
         "files", "wasm", "cli",
         {"WASM / wasmtime", "Plugin system", "LLM integration", "Polyglot (3+ langs)"},
         "good"),
    Tool("cloud-audit", "cloud", "Python", [], "medium", "permissive",
         "files", "none", "cli",
         {"MCP server", "LLM integration"},
         "good"),
    Tool("CERT UEFI Parser", "dfir", "Python", [], "medium", "permissive",
         "none", "none", "cli",
         {"Generated code"},
         "minimal"),
    Tool("mquire", "dfir", "Rust", [], "medium", "permissive",
         "in-memory", "none", "cli",
         {"YAML rules / templates", "Plugin system"},
         "good"),
    Tool("Little Snitch for Linux", "defense", "Rust", ["C"], "medium", "strong-copyleft",
         "files", "ebpf", "desktop-app",
         {"eBPF", "Polyglot (3+ langs)"},
         "minimal"),
    Tool("Allama", "defense", "Python", ["TypeScript"], "large", "strong-copyleft",
         "postgres", "nsjail", "service",
         {"YAML rules / templates", "LLM integration", "Plugin system",
          "Polyglot (3+ langs)", "MCP server"},
         "good"),
    Tool("Betterleaks", "appsec-secret", "Go", [], "medium", "permissive",
         "files", "none", "cli",
         {"CEL / Rego policy", "Plugin system"},
         "good"),

    # ----- Round 2 -----
    Tool("Trivy", "appsec-scanner", "Go", [], "huge", "permissive",
         "bbolt", "wasm", "cli",
         {"MCP server", "CEL / Rego policy", "WASM / wasmtime",
          "Plugin system", "Wire-format IR"},
         "corpus"),
    Tool("Buttercup", "appsec-ai", "Python", [], "huge", "permissive",
         "redis", "wasm", "service",
         {"LLM integration", "WASM / wasmtime", "Wire-format IR",
          "Polyglot (3+ langs)", "tree-sitter"},
         "good"),
    Tool("Seclab Taskflow Agent", "appsec-ai", "Python", [], "medium", "permissive",
         "files", "none", "cli",
         {"YAML rules / templates", "LLM integration", "MCP server", "Plugin system"},
         "good"),
    Tool("Nuclei", "perimeter-vuln", "Go", [], "huge", "permissive",
         "in-memory", "none", "cli",
         {"YAML rules / templates", "LLM integration", "Plugin system"},
         "corpus"),
    Tool("LibAFL", "appsec-fuzzer", "Rust", ["C"], "huge", "permissive",
         "files", "none", "library",
         {"Plugin system", "Polyglot (3+ langs)", "Generated code"},
         "corpus"),
    Tool("Hadrian", "api-sec", "Go", [], "medium", "permissive",
         "files", "none", "cli",
         {"YAML rules / templates", "LLM integration"},
         "good"),
    Tool("Caido", "perimeter-pentest", "—", [], "small", "commercial-leaning",
         "none", "none", "desktop-app",
         set(),
         "none",
         "closed source — public repo is brand/issues only"),
    Tool("PatchLeaks", "appsec-scanner", "Go", ["C"], "medium", "permissive",
         "files", "none", "web-app",
         {"LLM integration", "tree-sitter", "Generated code"},
         "minimal"),

    # ----- Round 3 -----
    Tool("AFL++", "appsec-fuzzer", "C", [], "huge", "permissive",
         "files", "none", "cli",
         {"Plugin system", "Generated code", "Polyglot (3+ langs)"},
         "corpus"),
    Tool("DefectDojo", "vuln-mgmt", "Python", ["JavaScript"], "huge", "weak-copyleft",
         "postgres", "none", "web-app",
         {"Plugin system", "YAML rules / templates"},
         "corpus"),
    Tool("Coraza", "appsec-waf", "Go", [], "large", "permissive",
         "in-memory", "wasm", "library",
         {"YAML rules / templates", "WASM / wasmtime", "Plugin system",
          "CEL / Rego policy", "Generated code"},
         "corpus",
         "tinygo build target"),
    Tool("Schemathesis", "api-sec", "Python", [], "large", "permissive",
         "files", "none", "library",
         {"YAML rules / templates", "Plugin system"},
         "corpus"),
    Tool("RESTler", "api-sec", "Python", ["F#"], "huge", "permissive",
         "files", "none", "cli",
         {"Generated code", "YAML rules / templates", "Polyglot (3+ langs)"},
         "corpus"),
    Tool("Trivy-MCP", "appsec-scanner", "Go", [], "small", "permissive",
         "in-memory", "none", "plugin",
         {"MCP server", "Plugin system"},
         "minimal",
         "bug: ScanFilesystemTool registered twice"),
    Tool("Vespasian", "api-discovery", "Go", [], "large", "permissive",
         "files", "none", "cli",
         {"Wire-format IR", "Plugin system"},
         "good",
         "auth detection missing from generated specs"),
    Tool("Ruzzy", "appsec-fuzzer", "Ruby", ["C"], "small", "permissive",
         "files", "none", "library",
         {"Generated code", "Plugin system"},
         "minimal"),

    # ----- Round 4 -----
    Tool("OWASP CRS", "appsec-waf", "Rules", [], "large", "permissive",
         "none", "none", "rules-only",
         {"YAML rules / templates", "CEL / Rego policy"},
         "corpus"),
    Tool("Sunshine", "vuln-mgmt", "Python", ["JavaScript"], "medium", "permissive",
         "none", "none", "web-app",
         {"Polyglot (3+ langs)"},
         "minimal"),
    Tool("Nettacker", "appsec-scanner", "Python", ["JavaScript"], "large", "weak-copyleft",
         "sqlite", "none", "multi",
         {"YAML rules / templates", "Plugin system", "Polyglot (3+ langs)"},
         "good",
         "YAML modules can run arbitrary Python via eval()"),
    Tool("ElectronSafeUpdater", "ref-design", "JavaScript", [], "small", "permissive",
         "files", "none", "library",
         {"Generated code"},
         "minimal",
         "manifest signatures NOT version-bound (literal 'version' bug)"),
    Tool("Katana", "perimeter-recon", "Go", [], "large", "permissive",
         "files", "none", "cli",
         {"Plugin system", "Wire-format IR"},
         "good"),
    Tool("httpx", "perimeter-recon", "Go", [], "large", "permissive",
         "in-memory", "none", "cli",
         {"Plugin system", "Wire-format IR"},
         "good"),
    Tool("akto", "api-sec", "Java", ["Go", "Python", "TypeScript", "Lua"],
         "huge", "permissive",
         "mongo", "none", "service",
         {"Kafka / msg bus", "YAML rules / templates", "LLM integration",
          "Plugin system", "Polyglot (3+ langs)", "MCP server"},
         "good",
         "hardcoded JWT bearer in IngestionAction.java:52"),
    Tool("Cherrybomb", "api-sec", "Rust", [], "medium", "permissive",
         "none", "none", "cli",
         {"Plugin system", "Generated code"},
         "good",
         "Profile::OWASP is todo!()"),
]

CATEGORY_LABEL = {
    "cicd": "CI/CD security",
    "cloud": "Cloud posture",
    "dfir": "DFIR / forensics",
    "defense": "Defensive ops",
    "appsec-scanner": "AppSec: scanners",
    "appsec-secret": "AppSec: secret scanning",
    "appsec-waf": "AppSec: WAF",
    "appsec-fuzzer": "AppSec: fuzzing",
    "appsec-ai": "AppSec: AI vuln research",
    "api-sec": "API security",
    "api-discovery": "API discovery",
    "perimeter-recon": "Perimeter: recon",
    "perimeter-pentest": "Perimeter: web pentest",
    "perimeter-vuln": "Perimeter: vuln scanning",
    "ref-design": "Reference designs",
    "vuln-mgmt": "Vuln management",
}

LANG_COLOR = {
    "Go":         "#00ADD8",
    "Python":     "#3776AB",
    "Rust":       "#CE422B",
    "C":          "#A8B9CC",
    "Java":       "#B07219",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "Ruby":       "#701516",
    "F#":         "#378BBA",
    "Lua":        "#000080",
    "Rules":      "#888888",
    "—":          "#cccccc",
}


# ============================================================================
# 1. Primary language distribution
# ============================================================================

def chart_language_dist() -> None:
    lang_counts = Counter(t.primary_lang for t in TOOLS)
    items = sorted(lang_counts.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    colors = [LANG_COLOR.get(L, "#888") for L in labels]

    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.7)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v),
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Number of analyzed tools (33 total)")
    ax.set_title("Primary implementation language across the 33 code-analyzed tools")
    ax.set_ylim(0, max(values) + 2.5)
    ax.grid(axis="x", visible=False)

    # Annotate polyglot count
    poly = sum(1 for t in TOOLS if t.extra_langs)
    ax.text(0.99, -0.22,
            f"{poly} of 33 tools ship code in 2+ languages — see polyglot pattern chart.",
            transform=ax.transAxes, ha="right", fontsize=8, color="#555")
    fig.savefig(OUT_DIR / "code-languages.png")
    plt.close(fig)


# ============================================================================
# 2. Architectural pattern adoption heatmap (33 tools x 12 patterns)
# ============================================================================

def chart_pattern_heatmap() -> None:
    sorted_tools = sorted(TOOLS, key=lambda t: (-len(t.patterns), t.name))
    n_tools = len(sorted_tools)
    n_patterns = len(PATTERNS)

    data = np.zeros((n_tools, n_patterns), dtype=int)
    for i, t in enumerate(sorted_tools):
        for j, p in enumerate(PATTERNS):
            if p in t.patterns:
                data[i, j] = 1

    fig, ax = plt.subplots(figsize=(11, 9))
    ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    for i in range(n_tools):
        for j in range(n_patterns):
            if data[i, j]:
                ax.text(j, i, "●", ha="center", va="center",
                        fontsize=10, color="#000", fontweight="bold")
    ax.set_xticks(np.arange(n_patterns))
    ax.set_xticklabels(PATTERNS, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(np.arange(n_tools))
    ax.set_yticklabels([t.name for t in sorted_tools], fontsize=8.5, fontweight="bold")
    ax.set_title("Architectural pattern adoption (33 tools × 12 patterns)")
    ax.grid(False)
    # Pattern frequency annotation at bottom
    freq = data.sum(axis=0)
    for j, f in enumerate(freq):
        ax.text(j, n_tools - 0.4, f"({f})", ha="center", va="top",
                fontsize=8, color="#777", fontstyle="italic")
    fig.savefig(OUT_DIR / "code-pattern-heatmap.png")
    plt.close(fig)


# ============================================================================
# 3. Storage / persistence backend
# ============================================================================

def chart_storage() -> None:
    storage_counts = Counter(t.storage for t in TOOLS)
    items = sorted(storage_counts.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    palette = {
        "files":     "#a8b9cc",
        "in-memory": "#dddddd",
        "bbolt":     "#3498db",
        "sqlite":    "#003B57",
        "mongo":     "#4DB33D",
        "postgres":  "#336791",
        "redis":     "#A41E11",
        "temporal":  "#7E57C2",
        "multi":     "#f39c12",
        "none":      "#bbbbbb",
    }
    colors = [palette.get(L, "#888") for L in labels]

    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.7)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, str(v),
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Tools")
    ax.set_title("Primary persistence backend across the 33 tools")
    ax.set_ylim(0, max(values) + 2.5)
    ax.grid(axis="x", visible=False)
    ax.text(0.99, -0.22,
            "'files' = plain JSON/YAML on disk;  'in-memory' = no on-disk state",
            transform=ax.transAxes, ha="right", fontsize=8, color="#555")
    fig.savefig(OUT_DIR / "code-storage.png")
    plt.close(fig)


# ============================================================================
# 4. Codebase size distribution
# ============================================================================

def chart_size() -> None:
    order = ["small", "medium", "large", "huge"]
    labels = {"small": "small\n(<3k LOC)", "medium": "medium\n(3-15k)",
              "large": "large\n(15-100k)", "huge": "huge\n(>100k)"}
    by_size_cat: dict[str, Counter] = {s: Counter() for s in order}
    for t in TOOLS:
        by_size_cat[t.size_bucket][t.category] += 1

    cat_order = ["appsec-scanner", "appsec-secret", "appsec-waf", "appsec-fuzzer",
                 "appsec-ai", "api-sec", "api-discovery", "perimeter-recon",
                 "perimeter-pentest", "perimeter-vuln", "cicd", "cloud",
                 "dfir", "defense", "ref-design", "vuln-mgmt"]
    cat_colors = plt.cm.tab20.colors[:len(cat_order)]
    color_map = dict(zip(cat_order, cat_colors))

    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(order))
    bottom = np.zeros(len(order))
    for cat in cat_order:
        vals = [by_size_cat[s].get(cat, 0) for s in order]
        if sum(vals) == 0:
            continue
        ax.bar(x, vals, bottom=bottom, color=color_map[cat],
               label=CATEGORY_LABEL[cat], edgecolor="white", linewidth=0.4)
        bottom = bottom + np.array(vals)
    totals = [sum(by_size_cat[s].values()) for s in order]
    for i, t_ in enumerate(totals):
        ax.text(i, t_ + 0.2, str(t_), ha="center", va="bottom",
                fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([labels[s] for s in order])
    ax.set_ylabel("Tools")
    ax.set_title("Codebase size distribution across the 33 tools, stacked by category")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=7.5)
    ax.grid(axis="x", visible=False)
    fig.savefig(OUT_DIR / "code-size.png")
    plt.close(fig)


# ============================================================================
# 5. Distribution form (CLI vs library vs service vs ...)
# ============================================================================

def chart_distribution() -> None:
    dist_counts = Counter(t.distribution for t in TOOLS)
    items = sorted(dist_counts.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    colors = plt.cm.Set2.colors[:len(labels)]

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.0f%%",
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5),
        pctdistance=0.78, textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("Distribution form across the 33 tools")
    ax.text(0, 0, f"{len(TOOLS)}\ntools", ha="center", va="center",
            fontsize=11, color="#333", fontweight="bold")
    fig.savefig(OUT_DIR / "code-distribution.png")
    plt.close(fig)


# ============================================================================
# 6. Test depth
# ============================================================================

def chart_tests() -> None:
    order = ["none", "minimal", "good", "corpus"]
    labels = {"none": "none", "minimal": "minimal\n(smoke only)",
              "good": "good\n(integration)", "corpus": "corpus\n(large/external)"}
    counts = Counter(t.tests for t in TOOLS)
    values = [counts.get(s, 0) for s in order]
    colors = ["#c0392b", "#f39c12", "#27ae60", "#2980b9"]

    fig, ax = plt.subplots(figsize=(8.0, 3.6))
    bars = ax.bar([labels[s] for s in order], values, color=colors,
                  edgecolor="white", linewidth=0.7)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v),
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Tools")
    ax.set_title("Test-suite depth across the 33 tools")
    ax.set_ylim(0, max(values) + 2)
    ax.grid(axis="x", visible=False)
    ax.text(0.99, -0.22,
            "'corpus' = ships a large external corpus (CRS FTW, Trivy fixtures, RESTler grammars, etc.)",
            transform=ax.transAxes, ha="right", fontsize=7.5, color="#555")
    fig.savefig(OUT_DIR / "code-tests.png")
    plt.close(fig)


# ============================================================================
# 7. License at code-level
# ============================================================================

def chart_license() -> None:
    cat_counts = Counter(t.license_class for t in TOOLS)
    order = ["permissive", "weak-copyleft", "strong-copyleft", "commercial-leaning"]
    values = [cat_counts.get(o, 0) for o in order]
    colors = ["#3498db", "#9b59b6", "#8e44ad", "#7f8c8d"]
    labels = ["Permissive\n(MIT/Apache/BSD)",
              "Weak copyleft\n(MPL-2.0)",
              "Strong copyleft\n(GPL/AGPL)",
              "Commercial-leaning\n(closed src)"]

    fig, ax = plt.subplots(figsize=(8, 3.4))
    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.7)
    for b, v in zip(bars, values):
        ax.text(v + 0.3, b.get_y() + b.get_height() / 2, str(v),
                va="center", fontsize=10, fontweight="bold")
    ax.set_xlabel("Tools")
    ax.set_title("License posture across the 33 code-analyzed tools")
    ax.set_xlim(0, max(values) + 3)
    ax.grid(axis="y", visible=False)
    fig.savefig(OUT_DIR / "code-licenses.png")
    plt.close(fig)


# ============================================================================

def main() -> None:
    chart_language_dist()
    chart_pattern_heatmap()
    chart_storage()
    chart_size()
    chart_distribution()
    chart_tests()
    chart_license()
    out = sorted(OUT_DIR.glob("code-*.png"))
    print(f"wrote {len(out)} code-analysis charts:")
    for p in out:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
