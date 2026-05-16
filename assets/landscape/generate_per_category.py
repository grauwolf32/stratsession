#!/usr/bin/env python3
"""
Generate per-category landscape charts.

Run with the project-local venv:
  /tmp/stratsession-viz/bin/python3 assets/landscape/generate_per_category.py

Outputs PNG files to assets/landscape/cat-*.png, each embedded into
the relevant report under reports/.

Each chart is built from a hand-curated dataset reflecting what's in
the per-category reports under reports/. When the underlying tools
change meaningfully, update the dataset at the top of each function.
"""

from __future__ import annotations

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


# Coverage colormap: white (none) → light → dark green (full)
COVERAGE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "coverage", ["#ffffff", "#dff0d8", "#7fc77f", "#2e7d32"]
)

def _annotate_heatmap(ax, data, fmt=None):
    """Write numeric or '·/◐/●' marks into each cell."""
    rows, cols = data.shape
    for i in range(rows):
        for j in range(cols):
            v = data[i, j]
            if fmt == "mark":
                mark = "·" if v == 0 else ("◐" if 0 < v < 1 else "●")
                color = "#888" if v == 0 else ("#000" if v >= 0.5 else "#666")
                ax.text(j, i, mark, ha="center", va="center",
                        fontsize=14, color=color, fontweight="bold")
            elif fmt == "num":
                ax.text(j, i, f"{v:g}", ha="center", va="center",
                        fontsize=9, color="#000" if v <= 50 else "white",
                        fontweight="bold")
            else:
                # default: just shading
                pass


# ============================================================================
# 1. CI/CD security — capability matrix
# ============================================================================

def chart_cicd_capability_matrix() -> None:
    tools = ["poutine", "zizmor", "Gato-X", "Plumber", "SmokedMeat"]
    classes = [
        "Workflow injection (SAST)",
        "Dangerous triggers detection",
        "Action pinning audit",
        "Permissions: scope audit",
        "Branch protection audit",
        "Runner secret extraction",
        "OIDC trust misconfig",
        "Cache poisoning",
        "LOTP payloads (live exec)",
        "Cloud pivot (AWS/GCP/Azure)",
        "Full kill-chain orchestration",
        "GitLab CI support",
    ]
    # Rows = tools, cols = classes. 0=none, 0.5=partial, 1=full.
    data = np.array([
        # poutine — SAST scanner from Boost
        [1, 1, 1, 1, 0, 0, 0.5, 0, 0, 0, 0, 0.5],
        # zizmor — Woodruff's GHA SAST
        [1, 1, 1, 1, 0, 0, 0.5, 0, 0, 0, 0, 0],
        # Gato-X — Adnan Khan's enum + abuse
        [0.5, 1, 0, 1, 1, 0.5, 0.5, 0.5, 0, 0, 0.5, 0],
        # Plumber — compliance scanner
        [0.5, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1],
        # SmokedMeat — full red-team framework
        [1, 1, 0.5, 1, 0, 1, 1, 1, 1, 1, 1, 0],
    ])

    fig, ax = plt.subplots(figsize=(9.5, 4.0))
    im = ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(classes)))
    ax.set_xticklabels(classes, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tools, fontsize=9, fontweight="bold")
    _annotate_heatmap(ax, data, fmt="mark")
    ax.set_title("CI/CD security — OSS capability coverage matrix")
    ax.grid(False)
    # Legend
    ax.text(0.0, -0.55, "Legend:  ·  none     ◐  partial     ●  full coverage",
            transform=ax.transAxes, fontsize=8, color="#444")
    ax.text(1.0, -0.55,
            "Source: stratsession reports/ci-cd-security.md + project READMEs",
            transform=ax.transAxes, fontsize=7, color="#777", ha="right")
    fig.savefig(OUT_DIR / "cat-cicd-capability-matrix.png")
    plt.close(fig)


# ============================================================================
# 2. Cloud posture — cloud-audit vs Prowler vs others
# ============================================================================

def chart_cloud_posture_compare() -> None:
    # Grouped bars over a few numeric dimensions.
    tools = ["cloud-audit", "Prowler", "CloudFox", "Pacu", "ScoutSuite"]
    metrics = {
        "AWS checks":                [94, 572, 0,  0,   100],
        "Attack-chain rules":        [31, 12,  18, 0,   0],
        "IAM escalation methods":    [61, 28,  22, 35,  0],
        "Compliance frameworks (AWS)":[6, 41,  0,  0,   12],
        "Multi-cloud providers":     [1, 14,  1,  3,   4],
    }
    colors = ["#3498db", "#27ae60", "#e67e22", "#c0392b", "#8e44ad"]

    fig, axes = plt.subplots(1, len(metrics), figsize=(13, 3.4), sharey=False)
    for ax, (metric, vals) in zip(axes, metrics.items()):
        bars = ax.bar(tools, vals, color=colors, edgecolor="white", linewidth=0.6)
        ax.set_title(metric, fontsize=10)
        ax.set_xticklabels(tools, rotation=35, ha="right", fontsize=8)
        ax.grid(axis="x", visible=False)
        # Annotate
        for b, v in zip(bars, vals):
            if v > 0:
                ax.text(b.get_x() + b.get_width()/2, v + max(vals)*0.02,
                        str(v), ha="center", va="bottom", fontsize=8, fontweight="bold")
    fig.suptitle("Cloud posture & attack — OSS scanner comparison (AWS-focused)",
                 fontsize=12, fontweight="bold", y=1.03)
    fig.text(0.99, -0.02,
             "Sources: cloud-audit README v2.2 (verified May 2026), Prowler README (verified Apr 2026), public READMEs.",
             ha="right", fontsize=7, color="#777")
    fig.savefig(OUT_DIR / "cat-cloud-compare.png")
    plt.close(fig)


# ============================================================================
# 3. AI vuln research — capability matrix
# ============================================================================

def chart_ai_vuln_research_matrix() -> None:
    tools = ["Buttercup\n(Trail of Bits)",
             "Atlantis\n(Team Atlanta)",
             "Theori CRS",
             "Seclab\nTaskflow Agent",
             "Trailmark\n(Trail of Bits)",
             "Pike\n(Synacktiv)"]
    caps = [
        "Bug discovery",
        "Auto-patching",
        "Multi-agent",
        "MCP server / consumer",
        "Multi-language SAST",
        "Fuzzing-integrated",
        "Callgraph / dataflow",
        "Production-grade (≥1 OSS bug)",
        "AIxCC finalist",
        "Defender-facing UX",
    ]
    # Rows = tools, cols = caps. 0/0.5/1.
    data = np.array([
        # Buttercup
        [1,1,1,0.5,1,1,1,1,1,0],
        # Atlantis
        [1,1,1,0.5,1,1,1,1,1,0],
        # Theori
        [1,1,1,0.5,1,1,0.5,1,1,0],
        # Seclab Taskflow Agent
        [1,0,1,1,1,0,1,1,0,0.5],
        # Trailmark
        [0.5,0,0,1,1,0,1,0.5,0,0.5],
        # Pike
        [0.5,0,0,0,0,0,0,0.5,0,1],
    ])

    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    im = ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(caps)))
    ax.set_xticklabels(caps, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tools, fontsize=8.5, fontweight="bold")
    _annotate_heatmap(ax, data, fmt="mark")
    ax.set_title("AI vulnerability research — OSS CRS / agent capability matrix")
    ax.grid(False)
    ax.text(0.0, -0.55, "Legend:  ·  none     ◐  partial     ●  full",
            transform=ax.transAxes, fontsize=8, color="#444")
    ax.text(1.0, -0.55,
            "Source: AIxCC finals announcement (Aug 2025), repo READMEs (May 2026).",
            transform=ax.transAxes, fontsize=7, color="#777", ha="right")
    fig.savefig(OUT_DIR / "cat-ai-vuln-research-matrix.png")
    plt.close(fig)


# ============================================================================
# 4. Scanners — Trivy/OSV-Scanner/Syft+Grype/Semgrep/Nuclei feature coverage
# ============================================================================

def chart_scanners_coverage() -> None:
    tools = ["Trivy", "OSV-Scanner", "Syft+Grype", "Semgrep", "Nuclei", "Bandit"]
    features = [
        "SCA (deps)",
        "Container image",
        "Filesystem / repo",
        "IaC misconfig",
        "Kubernetes runtime",
        "Secrets detection",
        "SBOM emit (CycloneDX)",
        "SBOM emit (SPDX)",
        "SAST patterns",
        "Reachability analysis",
        "AI-detected logic flaws",
        "MCP server",
        "VEX / EPSS / KEV enrich",
    ]
    # Rows = tools, cols = features.
    data = np.array([
        # Trivy
        [1,1,1,1,1,0.5,1,0.5,0,0,0,1,0.5],
        # OSV-Scanner
        [1,1,1,0,0,0,0.5,0,0,0,0,0,1],
        # Syft + Grype
        [1,1,1,0,0,0,1,1,0,0,0,0,1],
        # Semgrep
        [1,0,1,0.5,0,0.5,0,0,1,1,1,0,0.5],
        # Nuclei
        [0,0,0,0,0,0,0,0,0,0,1,0,0],
        # Bandit
        [0,0,1,0,0,0,0,0,1,0,0,0,0],
    ])

    fig, ax = plt.subplots(figsize=(10.5, 4.0))
    ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(features)))
    ax.set_xticklabels(features, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tools, fontsize=9, fontweight="bold")
    _annotate_heatmap(ax, data, fmt="mark")
    ax.set_title("Scanners — OSS feature coverage matrix")
    ax.grid(False)
    ax.text(0.0, -0.5, "Legend:  ·  none     ◐  partial     ●  full",
            transform=ax.transAxes, fontsize=8, color="#444")
    ax.text(1.0, -0.5,
            "Sources: reports/scanners.md (Trivy v0.70.0 verified, OSV-Scanner v2.3.5, Semgrep Apr 2026, Bandit 1.9.3).",
            transform=ax.transAxes, fontsize=7, color="#777", ha="right")
    fig.savefig(OUT_DIR / "cat-scanners-coverage.png")
    plt.close(fig)


# ============================================================================
# 5. API security — workflow position
# ============================================================================

def chart_api_security_workflow() -> None:
    # Stacked bars per tool, showing which workflow stages each covers.
    tools = ["Vespasian", "Hadrian", "akto", "schemathesis",
             "RESTler", "cherrybomb", "Julius"]
    stages = ["Discovery / capture",
              "Spec generation (OpenAPI/GraphQL)",
              "Spec audit (design flaws)",
              "Coverage / property fuzzing",
              "Stateful chain fuzzing",
              "AuthZ / role testing",
              "AI service fingerprinting"]
    colors = ["#3498db", "#16a085", "#27ae60", "#f39c12",
              "#e67e22", "#c0392b", "#8e44ad"]

    # Rows = tools, columns = stages, 0/0.5/1
    data = np.array([
        # Vespasian — discovery + spec gen
        [1, 1, 0, 0, 0, 0, 0],
        # Hadrian — authZ testing (YAML-driven), partial spec consumption
        [0, 0.5, 0, 0, 0, 1, 0],
        # akto — discovery + 1000+ tests (includes authZ)
        [1, 0.5, 0.5, 1, 0.5, 1, 0],
        # schemathesis — property-based fuzzing
        [0, 0, 0.5, 1, 0, 0, 0],
        # RESTler — stateful chains
        [0, 0, 0, 0.5, 1, 0, 0],
        # cherrybomb — spec audit
        [0, 0, 1, 0, 0, 0, 0],
        # Julius — AI service fingerprint
        [0.5, 0, 0, 0, 0, 0, 1],
    ])

    fig, ax = plt.subplots(figsize=(10, 4.0))
    y = np.arange(len(tools))
    left = np.zeros(len(tools))
    for j, (stage, color) in enumerate(zip(stages, colors)):
        widths = data[:, j]
        ax.barh(y, widths, left=left, color=color, edgecolor="white",
                linewidth=0.6, label=stage)
        for i, w in enumerate(widths):
            if w > 0:
                ax.text(left[i] + w/2, i, "●" if w == 1 else "◐",
                        ha="center", va="center", fontsize=11,
                        color="white" if w == 1 else "#fff", fontweight="bold")
        left = left + widths
    ax.set_yticks(y)
    ax.set_yticklabels(tools, fontsize=9, fontweight="bold")
    ax.set_xlabel("Stage coverage (● full, ◐ partial)")
    ax.set_xticks([])
    ax.set_title("API security — workflow stage coverage by tool")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=8)
    ax.grid(False)
    fig.savefig(OUT_DIR / "cat-api-workflow.png")
    plt.close(fig)


# ============================================================================
# 6. DFIR — platform × data-source coverage matrix
# ============================================================================

def chart_dfir_platform_matrix() -> None:
    tools = ["mquire", "Volatility 3", "CERT UEFI Parser",
             "chipsec", "UEFITool", "FLARE-VM", "AVML (acquire)"]
    cells = [
        "Linux memory", "Linux disk (page cache)",
        "Windows memory", "Windows disk",
        "macOS memory", "macOS disk",
        "Firmware (UEFI)", "Live system",
        "External symbols required",
    ]
    data = np.array([
        # mquire
        [1, 1, 0, 0, 0, 0, 0, 0, 0],
        # Volatility 3
        [1, 0.5, 1, 0.5, 1, 0.5, 0, 0, 1],   # external symbols required = 1
        # CERT UEFI Parser
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        # chipsec
        [0, 0, 0, 0, 0, 0, 1, 1, 0],
        # UEFITool
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        # FLARE-VM (RE provisioner; not really memory-acquire)
        [0, 0, 0.5, 0.5, 0, 0, 0, 1, 0],
        # AVML
        [1, 0, 0, 0, 0, 0, 0, 1, 0],
    ])

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(cells)))
    ax.set_xticklabels(cells, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tools, fontsize=9, fontweight="bold")
    _annotate_heatmap(ax, data, fmt="mark")
    ax.set_title("DFIR / forensics — platform × data-source coverage")
    ax.grid(False)
    ax.text(0.0, -0.55,
            "Note: rightmost column 'external symbols required' is a LIABILITY — green there means worse, not better.",
            transform=ax.transAxes, fontsize=7.5, color="#a04040", fontweight="bold")
    fig.savefig(OUT_DIR / "cat-dfir-platform-matrix.png")
    plt.close(fig)


# ============================================================================
# 7. Secret scanners — feature comparison
# ============================================================================

def chart_secret_scanners() -> None:
    tools = ["Gitleaks", "TruffleHog", "Betterleaks", "ggshield"]
    features = [
        "Regex / pattern detection",
        "Keyword pre-filter (Ahocorasick / similar)",
        "Shannon entropy filter",
        "BPE naturalness filter",
        "Live secret verification",
        "CEL filters (declarative)",
        "GitHub PR/issue/release scan (native)",
        "Drop-in Gitleaks config compat",
        "Detector breadth (≥500 types)",
    ]
    data = np.array([
        # Gitleaks
        [1, 0.5, 1, 0, 0, 0, 0, 1, 0.5],
        # TruffleHog
        [1, 0.5, 1, 0, 1, 0, 1, 0, 1],
        # Betterleaks
        [1, 1, 1, 1, 1, 1, 1, 1, 0.5],
        # ggshield
        [1, 0.5, 1, 0, 1, 0, 1, 0, 1],
    ])

    fig, ax = plt.subplots(figsize=(10, 3.3))
    ax.imshow(data, cmap=COVERAGE_CMAP, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(features)))
    ax.set_xticklabels(features, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels(tools, fontsize=9, fontweight="bold")
    _annotate_heatmap(ax, data, fmt="mark")
    ax.set_title("Secret scanners — OSS feature matrix")
    ax.grid(False)
    ax.text(0.0, -0.55, "Legend:  ·  none     ◐  partial     ●  full",
            transform=ax.transAxes, fontsize=8, color="#444")
    ax.text(1.0, -0.55, "Source: reports/secret-scanning.md (verified May 2026).",
            transform=ax.transAxes, fontsize=7, color="#777", ha="right")
    fig.savefig(OUT_DIR / "cat-secret-scanners.png")
    plt.close(fig)


# ============================================================================
# 8. C2 frameworks — language + transport + evasion comparison
# ============================================================================

def chart_c2_frameworks() -> None:
    tools = ["Sliver", "Mythic", "Empire 6.0", "Havoc",
             "C4", "SmokedMeat", "Beaconator", "Cobalt Strike (commercial)"]
    # Three sub-plots: language(s), transport count, evasion focus rating
    languages = ["Go", "Python+Docker", "Python+Go", "C/C++",
                 "Multi (WASM)", "Go", "Multi (orchestrator)", "Java/C"]
    transport_count = [6, 8, 5, 4, 3, 2, 5, 6]  # supported transports
    evasion = [3, 3, 2, 5, 2, 1, 3, 5]          # 1-5 evasion focus
    target_focus = ["General", "General", "AD/Win", "Windows",
                    "Cross-OS", "CI/CD only", "Listener mgmt", "General"]
    tool_focus_color = {
        "General": "#7f8c8d",
        "AD/Win": "#2980b9",
        "Windows": "#2980b9",
        "Cross-OS": "#27ae60",
        "CI/CD only": "#e67e22",
        "Listener mgmt": "#8e44ad",
    }
    colors = [tool_focus_color[t] for t in target_focus]

    fig = plt.figure(figsize=(11, 5.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1, 1], hspace=0.7, wspace=0.4)

    # (a) Transport count (bar)
    ax1 = fig.add_subplot(gs[0, 0])
    y = np.arange(len(tools))
    ax1.barh(y, transport_count, color=colors, edgecolor="white", linewidth=0.6)
    ax1.set_yticks(y); ax1.set_yticklabels(tools, fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("Supported transports (count)")
    ax1.set_title("Transport breadth", fontsize=10)
    for i, v in enumerate(transport_count):
        ax1.text(v + 0.1, i, str(v), va="center", fontsize=8)
    ax1.grid(axis="y", visible=False)

    # (b) Evasion rating (bar 1-5)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.barh(y, evasion, color=colors, edgecolor="white", linewidth=0.6)
    ax2.set_yticks(y); ax2.set_yticklabels(tools, fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 5.5)
    ax2.set_xlabel("Evasion focus (1=none, 5=high)")
    ax2.set_title("Evasion emphasis", fontsize=10)
    for i, v in enumerate(evasion):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=8)
    ax2.grid(axis="y", visible=False)

    # (c) Language pie
    ax3 = fig.add_subplot(gs[1, 0])
    lang_counts = {}
    for L in languages:
        lang_counts[L] = lang_counts.get(L, 0) + 1
    labels = list(lang_counts.keys())
    sizes = list(lang_counts.values())
    pie_colors = ["#3498db", "#27ae60", "#e67e22", "#c0392b", "#8e44ad", "#16a085", "#7f8c8d", "#f39c12"][:len(labels)]
    ax3.pie(sizes, labels=labels, colors=pie_colors,
            autopct="%1.0f%%", textprops={"fontsize": 8},
            wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.2))
    ax3.set_title("Implementation language", fontsize=10)

    # (d) Legend / focus key
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    ax4.set_title("Target focus (bar color)", fontsize=10)
    y0 = 0.95
    for focus, color in tool_focus_color.items():
        ax4.add_patch(plt.Rectangle((0.05, y0 - 0.03), 0.08, 0.06, color=color, transform=ax4.transAxes))
        ax4.text(0.16, y0, focus, transform=ax4.transAxes, va="center", fontsize=9)
        y0 -= 0.13

    fig.suptitle("C2 / red-team frameworks — comparison view", fontsize=12, fontweight="bold", y=1.00)
    fig.savefig(OUT_DIR / "cat-c2-frameworks.png")
    plt.close(fig)


# ============================================================================

def main() -> None:
    chart_cicd_capability_matrix()
    chart_cloud_posture_compare()
    chart_ai_vuln_research_matrix()
    chart_scanners_coverage()
    chart_api_security_workflow()
    chart_dfir_platform_matrix()
    chart_secret_scanners()
    chart_c2_frameworks()
    out = sorted(OUT_DIR.glob("cat-*.png"))
    print(f"wrote {len(out)} per-category charts:")
    for p in out:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
