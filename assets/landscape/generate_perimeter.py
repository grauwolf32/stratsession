#!/usr/bin/env python3
"""
Generate perimeter-stack analytical charts.

Run with the project-local venv:
  /tmp/stratsession-viz/bin/python3 assets/landscape/generate_perimeter.py

Outputs PNG files to assets/landscape/per-*.png. Embedded in reports/perimeter-stack.md.
"""

from __future__ import annotations

from pathlib import Path
from collections import Counter
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

PD_BLUE = "#1e3a8a"
PD_ACCENT = "#3b82f6"


def _annotate_marks(ax, data):
    rows, cols = data.shape
    for i in range(rows):
        for j in range(cols):
            v = data[i, j]
            mark = "·" if v == 0 else ("◐" if 0 < v < 1 else "●")
            color = "#888" if v == 0 else ("#000" if v >= 0.5 else "#666")
            ax.text(j, i, mark, ha="center", va="center",
                    fontsize=13, color=color, fontweight="bold")


# ============================================================================
# 1. Perimeter chain coverage — each tool × workflow stage
# ============================================================================

def chart_chain_coverage() -> None:
    tools = [
        ("subfinder",          "pd"),
        ("uncover",            "pd"),
        ("naabu",              "pd"),
        ("httpx",              "pd"),
        ("katana",             "pd"),
        ("nuclei",             "pd"),
        ("nuclei-templates",   "pd"),
        ("nuclei-ai-ext.",     "pd"),
        ("caido",              "other"),
        ("Vespasian",          "praetorian"),
        ("Hadrian",            "praetorian"),
        ("akto",               "other"),
        ("schemathesis",       "other"),
        ("RESTler",            "other"),
        ("cherrybomb",         "other"),
        ("Brutus",             "praetorian"),
        ("crAPI (target)",     "other"),
    ]
    stages = [
        "Subdomain enum",
        "Search-engine recon",
        "Port scan",
        "HTTP probe / fingerprint",
        "Crawl / endpoint discovery",
        "Manual web pentest (proxy)",
        "Templated CVE / misconfig",
        "API spec generation",
        "API spec audit",
        "API coverage fuzzing",
        "API stateful chain fuzz",
        "API authZ testing",
        "Credential testing",
        "Training target (vuln-by-design)",
    ]
    # Coverage matrix (rows = tools, cols = stages). 0/0.5/1.
    data = np.array([
        # subfinder
        [1,0,0,0,0,0,0,0,0,0,0,0,0,0],
        # uncover
        [0,1,0,0,0,0,0,0,0,0,0,0,0,0],
        # naabu
        [0,0,1,0,0,0,0,0,0,0,0,0,0,0],
        # httpx
        [0,0,0,1,0,0,0,0,0,0,0,0,0,0],
        # katana
        [0,0,0,0,1,0,0,0,0,0,0,0,0,0],
        # nuclei
        [0,0,0,0.5,0.5,0,1,0,0,0,0,0,0,0],
        # nuclei-templates
        [0,0,0,0,0,0,1,0,0,0,0,0,0,0],
        # nuclei-ai-extension
        [0,0,0,0,0,0,1,0,0,0,0,0,0,0],
        # caido
        [0,0,0,0,0,1,0,0,0,0,0,0,0,0],
        # Vespasian
        [0,0,0,0,0.5,0,0,1,0,0,0,0,0,0],
        # Hadrian
        [0,0,0,0,0,0,0,0.5,0,0,0,1,0,0],
        # akto
        [0,0,0,0,0,0,0.5,0.5,0.5,1,0.5,1,0,0],
        # schemathesis
        [0,0,0,0,0,0,0,0,0.5,1,0,0,0,0],
        # RESTler
        [0,0,0,0,0,0,0,0,0,0.5,1,0,0,0],
        # cherrybomb
        [0,0,0,0,0,0,0,0,1,0,0,0,0,0],
        # Brutus
        [0,0,0,0,0,0,0,0,0,0,0,0,1,0],
        # crAPI
        [0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    ])

    fig, ax = plt.subplots(figsize=(12.5, 6.5))
    ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(stages)))
    ax.set_xticklabels(stages, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))

    # Color tool labels by vendor cluster
    vendor_color = {"pd": PD_BLUE, "praetorian": "#c0392b", "other": "#444"}
    ax.set_yticklabels([t for t, _ in tools], fontsize=9, fontweight="bold")
    for tick, (_, v) in zip(ax.get_yticklabels(), tools):
        tick.set_color(vendor_color[v])

    _annotate_marks(ax, data)
    ax.set_title("Perimeter stack — coverage of the recon → discover → scan → fuzz → test chain")
    ax.grid(False)
    ax.text(0.0, -0.20,
            "Tool label color:  blue = ProjectDiscovery     red = Praetorian     gray = other",
            transform=ax.transAxes, fontsize=8.5, color="#444")
    ax.text(1.0, -0.20,
            "Cells:  · none    ◐ partial    ● primary capability",
            transform=ax.transAxes, fontsize=8, color="#666", ha="right")
    fig.savefig(OUT_DIR / "per-chain-coverage.png")
    plt.close(fig)


# ============================================================================
# 2. ProjectDiscovery ecosystem dominance
# ============================================================================

def chart_pd_dominance() -> None:
    # Show PD vs everyone else across the perimeter stack
    tools_by_vendor = {
        "ProjectDiscovery": ["subfinder", "uncover", "naabu", "httpx", "katana",
                              "nuclei", "nuclei-templates", "nuclei-ai-ext.",
                              "nuclei-templates-ai"],
        "Praetorian":      ["Vespasian", "Hadrian", "Julius", "Brutus", "nerva"],
        "Microsoft":       ["RESTler"],
        "OWASP":           ["crAPI", "ZAP (legacy)", "Amass (legacy)"],
        "Caido Labs":      ["caido"],
        "BLST":            ["cherrybomb"],
        "akto":            ["akto"],
        "Schemathesis":    ["schemathesis"],
    }
    vendors = list(tools_by_vendor.keys())
    counts = [len(v) for v in tools_by_vendor.values()]

    # Sort descending
    order = sorted(range(len(vendors)), key=lambda i: -counts[i])
    vendors = [vendors[i] for i in order]
    counts = [counts[i] for i in order]

    colors = [PD_BLUE if v == "ProjectDiscovery" else
              "#c0392b" if v == "Praetorian" else
              "#7f8c8d" for v in vendors]

    fig, ax = plt.subplots(figsize=(9.5, 4.0))
    y = np.arange(len(vendors))
    ax.barh(y, counts, color=colors, edgecolor="white", linewidth=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(vendors, fontsize=9, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlabel("Tools in the perimeter stack")
    ax.set_title("Vendor concentration in the 2026 OSS perimeter stack")
    for i, v in enumerate(counts):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=9, fontweight="bold")
    ax.grid(axis="y", visible=False)

    # Compute PD share
    total = sum(counts)
    pd_share = counts[0] / total * 100
    ax.text(0.99, -0.20,
            f"ProjectDiscovery alone supplies {counts[0]}/{total} tools = {pd_share:.0f}% of the curated OSS perimeter stack.",
            transform=ax.transAxes, ha="right", fontsize=8, color="#1e3a8a", fontweight="bold")
    fig.savefig(OUT_DIR / "per-pd-dominance.png")
    plt.close(fig)


# ============================================================================
# 3. Nuclei templates — what's in the box (counts by category)
# ============================================================================

def chart_nuclei_templates() -> None:
    """
    Approximate count of templates by major category in the
    nuclei-templates v10.4.x release line (May 2026 snapshot).
    """
    # Approximated from public template browser views and 12,000+ figure cited in
    # perimeter/README.md. Numbers are rough order-of-magnitude estimates intended
    # to show relative shape, not exact community counts. The headline 12,000 is
    # confirmed; sub-bucket distribution comes from spot-checks of the templates
    # repository's top-level directories.
    categories = {
        "CVEs":                       4500,
        "Vulnerabilities (general)":  1900,
        "Exposures (info/files)":     1500,
        "Misconfigurations":          1300,
        "Default logins / weak auth":  600,
        "Tech detection / fingerprint": 1100,
        "DNS / network":               500,
        "Cloud / SaaS":                400,
        "Other (DAST, workflows, …)":  200,
    }
    labels = list(categories.keys())
    values = list(categories.values())
    # Sort descending
    order = sorted(range(len(labels)), key=lambda i: -values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})

    # Left: bar chart of template count
    colors = ["#1e3a8a", "#3b82f6", "#60a5fa", "#93c5fd",
              "#bfdbfe", "#dbeafe", "#a5b4fc", "#c4b5fd", "#ddd6fe"]
    bars = ax1.barh(np.arange(len(labels)), values, color=colors, edgecolor="white", linewidth=0.6)
    ax1.set_yticks(np.arange(len(labels)))
    ax1.set_yticklabels(labels, fontsize=9, fontweight="bold")
    ax1.invert_yaxis()
    ax1.set_xlabel("Template count (approx, May 2026)")
    ax1.set_title("nuclei-templates v10.4.x — content by category")
    for i, v in enumerate(values):
        ax1.text(v + 50, i, f"{v:,}", va="center", fontsize=8)
    ax1.grid(axis="y", visible=False)

    # Right: timeline showing template-count growth + AI-template emergence
    years = ["2021", "2022", "2023", "2024", "2025", "2026"]
    community = [1000, 3500, 6500, 9000, 11000, 11700]
    ai_generated = [0, 0, 0, 0, 0, 300]  # nuclei-templates-ai repo emerged in 2026

    ax2.stackplot(years, community, ai_generated,
                  labels=["Community templates", "AI-generated templates"],
                  colors=[PD_BLUE, "#16a085"], alpha=0.9, edgecolor="white", linewidth=0.5)
    ax2.set_ylim(0, 13000)
    ax2.set_title("Nuclei template-count growth")
    ax2.set_ylabel("Active templates")
    ax2.set_xlabel("Year")
    ax2.legend(loc="upper left", frameon=False, fontsize=8)

    # Annotate total
    total = sum(values)
    ax2.text(0.99, 0.02, f"v10.4.x total: ≈{total:,}",
             transform=ax2.transAxes, ha="right", fontsize=8, color="#1e3a8a", fontweight="bold")
    ax2.text(0.99, -0.16,
             "AI-generated templates: separate repo projectdiscovery/nuclei-templates-ai (2026 Q1).",
             transform=ax2.transAxes, ha="right", fontsize=7, color="#777")
    fig.savefig(OUT_DIR / "per-nuclei-templates.png")
    plt.close(fig)


# ============================================================================
# 4. Recon tools deep comparison — subfinder, uncover, amass, naabu, httpx, katana
# ============================================================================

def chart_recon_compare() -> None:
    tools = ["subfinder", "uncover", "amass", "naabu", "httpx", "katana"]
    dims = [
        "Passive subdomain discovery",
        "Search-engine recon (Shodan/Censys/Fofa)",
        "Active DNS resolution",
        "Legal-entity / WHOIS / RDAP",
        "TCP port scanning",
        "HTTP probing",
        "Tech / WAF fingerprinting",
        "Crawling / endpoint discovery",
        "JavaScript-rendering (headless)",
        "Output JSON for pipelines",
        "Active maintenance (2025-2026)",
    ]
    data = np.array([
        # subfinder
        [1, 0, 0.5, 0, 0, 0, 0, 0, 0, 1, 1],
        # uncover
        [0.5, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1],
        # amass
        [1, 0.5, 1, 1, 0, 0, 0, 0, 0, 1, 0.5],
        # naabu
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1],
        # httpx
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        # katana
        [0, 0, 0, 0, 0, 0, 0.5, 1, 1, 1, 1],
    ])

    fig, ax = plt.subplots(figsize=(11, 4.0))
    ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(dims)))
    ax.set_xticklabels(dims, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tools, fontsize=9, fontweight="bold")
    _annotate_marks(ax, data)
    ax.set_title("External recon — OSS tool coverage matrix")
    ax.grid(False)
    ax.text(0.0, -0.4, "Legend:  ·  none     ◐  partial     ●  primary capability",
            transform=ax.transAxes, fontsize=8, color="#444")
    ax.text(1.0, -0.4,
            "All except amass are ProjectDiscovery tools — the recon layer is essentially a single-vendor stack.",
            transform=ax.transAxes, ha="right", fontsize=8, color=PD_BLUE, fontweight="bold")
    fig.savefig(OUT_DIR / "per-recon-compare.png")
    plt.close(fig)


def main() -> None:
    chart_chain_coverage()
    chart_pd_dominance()
    chart_nuclei_templates()
    chart_recon_compare()
    out = sorted(OUT_DIR.glob("per-*.png"))
    print(f"wrote {len(out)} perimeter charts:")
    for p in out:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
