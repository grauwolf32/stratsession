#!/usr/bin/env python3
"""
Generate landscape charts for reports/landscape-analysis.md.

Run with the project-local venv:
  /tmp/stratsession-viz/bin/python3 assets/landscape/generate.py

Outputs PNG files to assets/landscape/.

The tool inventory is curated from TOOLS.md and the deep-dive reports under
reports/. It is intentionally a snapshot, not a live scrape; update when
TOOLS.md changes meaningfully.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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

# Palette: muted, print-friendly, distinct.
PALETTE = {
    "offense":    "#c0392b",
    "defense":    "#2980b9",
    "research":   "#8e44ad",
    "dual":       "#f39c12",
    "ai":         "#16a085",
    "kube":       "#27ae60",
    "cloud":      "#3498db",
    "cicd":       "#e67e22",
    "appsec":     "#9b59b6",
    "id":         "#1abc9c",
    "fuzz":       "#c0392b",
    "dfir":       "#34495e",
    "recon":      "#7f8c8d",
    "llm":        "#e74c3c",
    "hw":         "#95a5a6",
}

# ----------------------------------------------------------------------------
# Curated inventory. Fields:
#   name, category, side, year, quarter, license, vendor, mcp, agpl_or_gpl
# Quarter:  Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec; "?"=approx
#
# Side codes:
#   off = offensive (red-team / attack tooling)
#   def = defensive (detection, posture, scanning, response)
#   dual = used by both (e.g. training labs, MCP wrappers)
#   res = research-only with no clear side
#
# Category codes (kept short for chart labels):
#   ai   = AI vuln research / agentic
#   appsec = SAST/SCA/SBOM/secret
#   cicd = CI/CD security
#   cloud = cloud posture & attack
#   c2   = C2 / red-team framework
#   kube = K8s / container security
#   id   = identity / AD / Entra
#   api  = API security
#   fuzz = fuzzing
#   dfir = DFIR / forensics / reversing
#   llm  = LLM red-team / prompt-injection
#   recon = recon / OSINT
#   hw   = hardware / firmware / mobile
#   defops = host-firewall + SOAR
# ----------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    category: str
    side: str
    year: int
    quarter: int          # 1..4, 0 = unknown
    license: str
    vendor: str
    mcp: bool = False
    agpl_or_gpl: bool = False  # AGPL-3.0 or GPL-2.0/3.0 (copyleft, sticky)


# Order roughly by year/quarter to make timeline clearer.
TOOLS: list[Tool] = [
    # ---- 2025 ----
    # AI vuln research (AIxCC wave)
    Tool("Buttercup",                 "ai",   "dual","2025", 3, "Apache-2.0", "Trail of Bits"),
    Tool("Atlantis (Team Atlanta)",   "ai",   "dual","2025", 3, "Apache-2.0", "Team Atlanta"),
    Tool("Theori CRS",                "ai",   "dual","2025", 3, "Apache-2.0", "Theori"),

    # SAST/SCA/SBOM
    Tool("PatchLeaks",                "appsec","def","2025", 3, "MIT",        "hatlesswizard"),
    Tool("Sunshine",                  "appsec","def","2025", 2, "Apache-2.0", "OWASP CycloneDX"),

    # Kubernetes / Cloud / Container
    Tool("Spotter",                   "kube","def", "2025", 3, "Apache-2.0", "Madhu Akula"),
    Tool("KIEMPossible",              "kube","def", "2025", 3, "Apache-2.0", "Palo Alto"),
    Tool("Copacetic (emphasis)",      "kube","def", "2025", 4, "Apache-2.0", "CNCF/Copa"),
    Tool("Stratoshark",               "kube","def", "2025", 4, "GPL-2.0",    "Sysdig",     agpl_or_gpl=True),
    Tool("HoneyBee",                  "kube","def", "2025", 3, "MIT",        "yaaras"),

    # Cloud attack
    Tool("EntraGoat",                 "cloud","off","2025", 3, "MIT",        "Semperis"),
    Tool("SAMLSmith",                 "cloud","off","2025", 3, "MIT",        "Semperis"),
    Tool("OAuthSeeker",               "cloud","off","2025", 3, "Apache-2.0", "Praetorian"),

    # Identity / AD
    # (BloodHound/AzureHound are pre-existing; only counting *new* 2025-2026 stuff)
    # Identity-flavored Cryptosploit, Angry Magpie etc.
    Tool("Cryptosploit",              "appsec","off","2025", 3, "MIT",        "nullpsifer"),
    Tool("Angry Magpie",              "appsec","off","2025", 3, "MIT",        "SquareX"),
    Tool("DVBE",                      "appsec","dual","2025", 3, "MIT",        "infosecak"),

    # C2 / red-team
    Tool("Empire 6.0",                "c2", "off","2025", 3, "BSD-3-Clause","BC-SECURITY"),
    Tool("C4",                        "c2", "off","2025", 3, "MIT",        "Scott Taylor"),
    Tool("Beaconator",                "c2", "off","2025", 3, "MIT",        "CrowdStrike"),
    Tool("GlytchC2",                  "c2", "off","2025", 3, "MIT",        "ccelikanil"),
    Tool("BOAZ",                      "c2", "off","2025", 3, "MIT",        "thomasxm"),
    Tool("WarHead",                   "c2", "off","2025", 3, "MIT",        "Malienist"),
    Tool("AIMaL",                     "c2", "off","2025", 3, "MIT",        "Endrit Shaqiri"),
    Tool("Messenger",                 "c2", "off","2025", 3, "MIT",        "Skyler Knecht"),
    Tool("Blackdagger",               "c2", "off","2025", 3, "MIT",        "Erdem Ozgen"),

    # LLM / agent red-team
    Tool("promptmap2",                "llm","off","2025", 3, "MIT",        "Utku Sen"),
    Tool("MPIT",                      "llm","off","2025", 3, "MIT",        "Sh1n0g1"),
    Tool("mcp-snitch",                "llm","def","2025", 3, "MIT",        "Adversis"),
    Tool("Sketchy",                   "llm","def","2025", 3, "MIT",        "Adversis"),

    # DFIR
    Tool("Garuda",                    "dfir","def","2025", 3, "MIT",        "Monnappa"),
    Tool("Lex Sleuther",              "dfir","def","2025", 3, "MIT",        "CrowdStrike"),
    Tool("RETINA",                    "dfir","def","2025", 3, "MIT",        "cecio"),
    Tool("Attack Flow Detector",      "dfir","def","2025", 3, "MIT",        "Ezzeldin Adel"),

    # Recon
    Tool("Robin",                     "recon","off","2025", 3, "MIT",        "Apurv Singh Gautam"),
    Tool("TheTimeMachine",            "recon","off","2025", 3, "MIT",        "Anmol Sachan"),

    # Hardware
    Tool("Tengu Marauder v2",         "hw","off","2025", 3, "MIT",          "ExMachina"),

    # ---- 2026 ----
    # AI vuln research
    Tool("Seclab Taskflow Agent",     "ai","dual","2026", 1, "MIT",       "GitHub Sec Lab"),
    Tool("Trailmark",                 "ai","dual","2026", 1, "Apache-2.0","Trail of Bits"),
    Tool("Pike",                      "ai","def","2026", 1, "Apache-2.0", "Synacktiv"),

    # AppSec / scanners
    Tool("Trivy MCP",                 "appsec","def","2026", 1, "Apache-2.0","Aqua",    mcp=True),
    Tool("Betterleaks",               "appsec","def","2026", 2, "MIT",       "Aikido/Zach Rice"),

    # Cloud
    Tool("maSSO",                     "cloud","off","2026", 1, "Apache-2.0","Doyensec"),
    Tool("ForceHound",                "cloud","off","2026", 1, "Apache-2.0","NetSPI"),
    Tool("cloud-audit",               "cloud","def","2026", 1, "MIT",       "HAIT/Mariusz Gebala", mcp=True),

    # API security
    Tool("Vespasian",                 "api","off","2026", 1, "Apache-2.0","Praetorian"),
    Tool("Hadrian",                   "api","off","2026", 1, "Apache-2.0","Praetorian", mcp=True),
    Tool("Julius",                    "api","dual","2026", 1, "Apache-2.0","Praetorian"),

    # CI/CD wave (post-TeamPCP)
    Tool("SmokedMeat",                "cicd","off","2026", 2, "AGPL-3.0",  "Boost Security Labs", agpl_or_gpl=True),
    Tool("Plumber",                   "cicd","def","2026", 1, "MPL-2.0",   "getplumber/r2devops"),
    Tool("Brutus",                    "cicd","off","2026", 1, "Apache-2.0","Praetorian"),

    # DFIR / forensics
    Tool("CERT UEFI Parser",          "dfir","def","2026", 1, "MIT",       "CMU/SEI CERT"),
    Tool("mquire",                    "dfir","def","2026", 1, "Apache-2.0","Trail of Bits"),
    Tool("CoBRA",                     "dfir","def","2026", 1, "Apache-2.0","Trail of Bits"),

    # Defensive ops
    Tool("Little Snitch for Linux",   "defops","def","2026", 2, "GPL-2.0", "Objective Development", agpl_or_gpl=True),
    Tool("Allama",                    "defops","def","2026", 1, "AGPL-3.0","digitranslab", agpl_or_gpl=True),

    # Identity / app
    Tool("SafeUpdater",               "appsec","def","2026", 1, "Apache-2.0","Doyensec"),

    # MSSQLHound rewrite
    Tool("MSSQLHound (Go rewrite)",   "id","off","2026", 1, "Apache-2.0","SpecterOps"),
]


# ============================================================================
# Chart 1: releases by quarter (2025 H2 vs 2026 H1)
# ============================================================================

def chart_releases_by_quarter() -> None:
    bucket: Counter[str] = Counter()
    for t in TOOLS:
        key = f"{t.year}-Q{t.quarter}" if t.quarter else f"{t.year}-Q?"
        bucket[key] += 1

    order = ["2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"]
    counts = [bucket.get(k, 0) for k in order]

    # Stack by side for visual richness.
    side_counts: dict[str, list[int]] = {"off": [0]*len(order), "def": [0]*len(order), "dual": [0]*len(order)}
    for t in TOOLS:
        key = f"{t.year}-Q{t.quarter}"
        if key in order:
            i = order.index(key)
            side_counts.setdefault(t.side, [0]*len(order))[i] += 1

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    x = np.arange(len(order))
    bottom = np.zeros(len(order))
    colors = {"off": PALETTE["offense"], "def": PALETTE["defense"], "dual": PALETTE["dual"], "res": "#bdc3c7"}
    labels = {"off": "Offensive", "def": "Defensive", "dual": "Dual-use / research"}

    for side in ["def", "off", "dual"]:
        vals = side_counts.get(side, [0]*len(order))
        ax.bar(x, vals, bottom=bottom, color=colors[side], label=labels.get(side, side), edgecolor="white", linewidth=0.5)
        bottom = bottom + np.array(vals)

    # Total label on top of each bar.
    for i, total in enumerate(counts):
        ax.text(i, total + 0.4, str(total), ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(order)
    ax.set_ylabel("OSS tool releases (curated)")
    ax.set_title("OSS security-tool releases by quarter, May 2025 → May 2026")
    ax.set_ylim(0, max(counts) + 3)
    ax.legend(loc="upper right", frameon=False)
    ax.text(0.99, -0.18, "Source: stratsession TOOLS.md (curated 2025–2026 inventory). 2026-Q2 is partial (through May 16).",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#555")

    fig.savefig(OUT_DIR / "01-releases-by-quarter.png")
    plt.close(fig)


# ============================================================================
# Chart 2: tools by category (horizontal bar)
# ============================================================================

CATEGORY_LABEL = {
    "ai":     "AI vuln research / agentic",
    "appsec": "AppSec (SAST/SCA/SBOM/secret)",
    "api":    "API security",
    "cicd":   "CI/CD security",
    "cloud":  "Cloud posture & attack",
    "c2":     "C2 / red-team frameworks",
    "kube":   "Kubernetes / container",
    "id":     "Identity / AD / Entra",
    "fuzz":   "Fuzzing",
    "dfir":   "DFIR / forensics / reversing",
    "llm":    "LLM red-team",
    "recon":  "Recon / OSINT",
    "hw":     "Hardware / firmware",
    "defops": "Defensive ops (host FW + SOAR)",
}

CATEGORY_COLOR = {
    "ai":    PALETTE["ai"],
    "appsec":PALETTE["appsec"],
    "api":   PALETTE["appsec"],
    "cicd":  PALETTE["cicd"],
    "cloud": PALETTE["cloud"],
    "c2":    PALETTE["offense"],
    "kube":  PALETTE["kube"],
    "id":    PALETTE["id"],
    "fuzz":  PALETTE["fuzz"],
    "dfir":  PALETTE["dfir"],
    "llm":   PALETTE["llm"],
    "recon": PALETTE["recon"],
    "hw":    PALETTE["hw"],
    "defops":PALETTE["defense"],
}

def chart_categories() -> None:
    cat_counts: Counter[str] = Counter(t.category for t in TOOLS)
    items = sorted(cat_counts.items(), key=lambda kv: kv[1])
    labels = [CATEGORY_LABEL.get(c, c) for c, _ in items]
    values = [v for _, v in items]
    colors = [CATEGORY_COLOR.get(c, "#777") for c, _ in items]

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    y = np.arange(len(items))
    ax.barh(y, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Tool count")
    ax.set_title("Curated OSS tool count by category, May 2025 → May 2026")
    for i, v in enumerate(values):
        ax.text(v + 0.15, i, str(v), va="center", fontsize=9, color="#333")
    ax.grid(axis="y", visible=False)
    fig.savefig(OUT_DIR / "02-categories.png")
    plt.close(fig)


# ============================================================================
# Chart 3: license distribution (donut)
# ============================================================================

def chart_licenses() -> None:
    lic_counts: Counter[str] = Counter(t.license for t in TOOLS)
    # Order by count descending, keep top 5, group rest as "Other".
    items = lic_counts.most_common()
    labels = [k for k, _ in items]
    sizes = [v for _, v in items]
    colors = ["#3498db", "#2ecc71", "#9b59b6", "#e67e22", "#e74c3c", "#95a5a6", "#1abc9c", "#34495e"]
    colors = colors[:len(items)]

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.0f%%",
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5),
        pctdistance=0.78, textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("License distribution across curated 2025–2026 OSS")
    # Center annotation: AGPL/GPL count
    sticky_count = sum(1 for t in TOOLS if t.agpl_or_gpl)
    total = len(TOOLS)
    ax.text(0, 0, f"{sticky_count}/{total}\nAGPL/GPL\n(sticky)",
            ha="center", va="center", fontsize=9, color="#333")
    fig.savefig(OUT_DIR / "03-licenses.png")
    plt.close(fig)


# ============================================================================
# Chart 4: vendor / org concentration (top contributors)
# ============================================================================

def chart_vendors() -> None:
    vendor_counts: Counter[str] = Counter(t.vendor for t in TOOLS)
    # Group into top-N + "others"
    N = 10
    items = vendor_counts.most_common(N)
    other_count = sum(v for _, v in vendor_counts.most_common()[N:])
    if other_count:
        items.append(("(other 30+ contributors)", other_count))
    items = list(reversed(items))  # bottom-up for barh
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    y = np.arange(len(items))
    # Highlight Praetorian + Trail of Bits + Boost Security + Doyensec (the OSS-pipeline orgs)
    PIPELINE_ORGS = {"Praetorian", "Trail of Bits", "Boost Security Labs", "Doyensec", "GitHub Sec Lab"}
    colors = [PALETTE["offense"] if k in PIPELINE_ORGS else "#7f8c8d" for k in labels]
    ax.barh(y, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("OSS tools shipped in window")
    ax.set_title("Vendor / author concentration (top 10)")
    for i, v in enumerate(values):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=9, color="#333")
    ax.grid(axis="y", visible=False)
    # Legend
    p1 = mpatches.Patch(color=PALETTE["offense"], label="Post-engagement OSS pipeline orgs")
    p2 = mpatches.Patch(color="#7f8c8d", label="Other vendors / individuals")
    ax.legend(handles=[p1, p2], loc="lower right", frameon=False, fontsize=8)
    fig.savefig(OUT_DIR / "04-vendors.png")
    plt.close(fig)


# ============================================================================
# Chart 5: MCP-server adoption rate by half
# ============================================================================

def chart_mcp_adoption() -> None:
    # Group by half-year.
    def half(y, q):
        return f"{y}-H{1 if q <= 2 else 2}"
    halves = ["2025-H1", "2025-H2", "2026-H1"]
    total = {h: 0 for h in halves}
    mcp = {h: 0 for h in halves}
    for t in TOOLS:
        h = half(t.year, t.quarter)
        if h not in total:
            continue
        total[h] += 1
        if t.mcp:
            mcp[h] += 1

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    x = np.arange(len(halves))
    width = 0.4

    totals = [total[h] for h in halves]
    mcps = [mcp[h] for h in halves]
    pcts = [100 * m / t if t else 0 for m, t in zip(mcps, totals)]

    ax.bar(x - width/2, totals, width, color="#bdc3c7", label="Total releases", edgecolor="white", linewidth=0.5)
    ax.bar(x + width/2, mcps, width, color=PALETTE["ai"], label="Ships an MCP server", edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(halves)
    ax.set_ylabel("Tool count")
    ax.set_title("MCP-server adoption: half-yearly")

    # Annotate % above each MCP bar
    for i, (m, p) in enumerate(zip(mcps, pcts)):
        ax.text(i + width/2, m + 0.3, f"{m} ({p:.0f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")
    for i, t_ in enumerate(totals):
        ax.text(i - width/2, t_ + 0.3, str(t_), ha="center", va="bottom", fontsize=9, color="#555")

    ax.legend(loc="upper left", frameon=False)
    ax.text(0.99, -0.18,
            "MCP servers turn a CLI into an agent-callable capability. Pattern emerged with Trivy MCP (Q1 2026); now spreading.",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#555")
    fig.savefig(OUT_DIR / "05-mcp-adoption.png")
    plt.close(fig)


# ============================================================================
# Chart 6: AGPL/GPL share over time
# ============================================================================

def chart_agpl_share() -> None:
    halves = ["2025-H1", "2025-H2", "2026-H1"]
    total = {h: 0 for h in halves}
    sticky = {h: 0 for h in halves}
    for t in TOOLS:
        h = f"{t.year}-H{1 if t.quarter <= 2 else 2}"
        if h not in total:
            continue
        total[h] += 1
        if t.agpl_or_gpl:
            sticky[h] += 1
    pcts = [100 * sticky[h] / total[h] if total[h] else 0 for h in halves]

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    ax.plot(halves, pcts, marker="o", linewidth=2.5, markersize=8, color="#8e44ad")
    for x, y in zip(halves, pcts):
        ax.text(x, y + 1.5, f"{y:.0f}%", ha="center", fontsize=9, fontweight="bold", color="#8e44ad")
    ax.set_ylim(0, max(pcts) + 8)
    ax.set_ylabel("% of releases under AGPL or GPL")
    ax.set_title("Copyleft (AGPL/GPL) share — sticky-licensing trend")
    ax.text(0.99, -0.20,
            "Boost (SmokedMeat AGPL-3.0), digitranslab (Allama AGPL-3.0), Objective Development (Little Snitch GPL-2.0), Sysdig (Stratoshark GPL-2.0).",
            transform=ax.transAxes, ha="right", va="top", fontsize=7, color="#555")
    fig.savefig(OUT_DIR / "06-agpl-share.png")
    plt.close(fig)


# ============================================================================
# Chart 7: offense / defense balance by category
# ============================================================================

def chart_offense_defense() -> None:
    cats = list(CATEGORY_LABEL.keys())
    off = {c: 0 for c in cats}
    def_ = {c: 0 for c in cats}
    dual = {c: 0 for c in cats}
    for t in TOOLS:
        if t.category not in off:
            continue
        if t.side == "off":   off[t.category]   += 1
        elif t.side == "def": def_[t.category]  += 1
        else:                 dual[t.category]  += 1

    # Drop empty cats, sort by total
    items = []
    for c in cats:
        total = off[c] + def_[c] + dual[c]
        if total:
            items.append((c, off[c], def_[c], dual[c], total))
    items.sort(key=lambda x: x[4])

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    y = np.arange(len(items))
    labels = [CATEGORY_LABEL[c] for c, *_ in items]
    offs = np.array([o for _, o, *_ in items])
    defs = np.array([d for _, _, d, *_ in items])
    duals = np.array([du for _, _, _, du, _ in items])

    ax.barh(y, offs, color=PALETTE["offense"], label="Offensive", edgecolor="white", linewidth=0.5)
    ax.barh(y, defs, left=offs, color=PALETTE["defense"], label="Defensive", edgecolor="white", linewidth=0.5)
    ax.barh(y, duals, left=offs + defs, color=PALETTE["dual"], label="Dual / research", edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Tool count")
    ax.set_title("Offense / defense balance, by category")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="y", visible=False)
    fig.savefig(OUT_DIR / "07-offense-defense.png")
    plt.close(fig)


def main() -> None:
    chart_releases_by_quarter()
    chart_categories()
    chart_licenses()
    chart_vendors()
    chart_mcp_adoption()
    chart_agpl_share()
    chart_offense_defense()
    print(f"wrote {len(list(OUT_DIR.glob('*.png')))} charts to {OUT_DIR}")


if __name__ == "__main__":
    main()
