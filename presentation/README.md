# Perimeter Security: New OSS Tools & Approaches (2025-2026)

A strategy-session presentation plan covering the recent open-source tools for perimeter security, paired with hands-on test scenarios so the deck can be field-tested before the talk.

## Audience

- **Primary**: Technical leaders making OSS-adoption and AppSec/SecOps tooling-roadmap decisions.
- **Secondary**: Security engineers who will run the test scenarios after the talk.

## Talk parameters

- **Length**: ~60 minutes (28 slides × ~2 minutes/slide + Q&A).
- **Slide budget**: 28 slides hard cap (within the ≤30 ceiling, leaves room for one or two cuts during rehearsal).
- **Format**: assumes a markdown-to-slides pipeline (marp / reveal / Google Slides import). Slide content is described in [`slides.md`](./slides.md).
- **Live demo**: 2-3 minutes of one tool live (recommendation: Hadrian's three-phase mutation test against crAPI). Pre-recorded fallback per scenario in case live demo fails.

## Repo layout

```
presentation/
├── README.md           ← this file: plan, audience, narrative arc, key takeaways
├── slides.md           ← slide-by-slide outline (28 slides)
└── test-scenarios/
    ├── README.md       ← test index + tool-to-test-to-slide matrix
    ├── 00-environment-setup.md
    ├── 01-recon-chain.md
    ├── 02-templated-scanning.md
    ├── 03-modern-dast.md
    ├── 04-api-discovery-authz.md
    ├── 05-api-fuzzing.md
    ├── 06-api-platform.md
    └── 07-spec-audit-waf-ai.md
```

## Narrative arc

The deck follows three movements:

1. **Why now (slides 1-5)** — what changed in 2024-2026 that makes a refresh of perimeter tooling worth a strategy session. The story: AI-assisted attacks, the API attack-surface explosion, agentic AI exposing new perimeter, the OSS-vs-commercial gap closing, and supply-chain incidents (Trivy 2026) raising the bar on tool selection.
2. **What's new (slides 6-22)** — five clusters of recent OSS tooling, each with a representative tool and a test scenario marker:
   - Modern recon (ProjectDiscovery suite + Uncover)
   - Templated + AI-driven scanning (Nuclei v3.8 + AI extensions)
   - Modern DAST (Caido as Burp alternative)
   - Recent API security stack (Vespasian/Hadrian + Akto + Schemathesis + RESTler + Cherrybomb)
   - AI-assisted vuln research at the perimeter (Buttercup, Taskflow Agent)
3. **How to deploy (slides 23-28)** — recommended stack, POC priorities, environment setup, risks (supply-chain pinning, LLM costs), and decision framework.

## Key takeaways the deck must leave with the audience

1. **2024-2026 OSS perimeter tooling is materially better than 2022 OSS** — not incremental.
2. **API security is the perimeter category with the biggest OSS jump** — Vespasian + Hadrian + Akto + Schemathesis + RESTler + Cherrybomb covers 90% of what commercial API-security platforms offer.
3. **AI integration is real and operational, not research** — Nuclei AI template generation, Buttercup CRS, Taskflow Agent, Hadrian's `--planner` are all deployable today.
4. **Caido is the standout modern DAST** — Rust + sleek UX + active development; the credible OSS Burp alternative for the first time in 5+ years.
5. **The 2026 Trivy supply-chain incident changed tool-adoption hygiene** — commit-SHA pinning and dependency cooldowns are now table stakes.

## Verifiable evidence base

All factual claims map to material already verified in this repo:

- **Tool list**: 15 submodules under [`../sources/perimeter/`](../sources/perimeter/) — every version pinned and reachable.
- **Recent advancements**: [`../reports/api-security.md`](../reports/api-security.md) and [`../reports/scanners.md`](../reports/scanners.md) (extended sections with 2025-2026 advancements + landscape context).
- **Practitioner evidence**: [`../blogs/oss-usage-case-studies.md`](../blogs/oss-usage-case-studies.md) — adoption stories, scaling guidance, supply-chain incidents.
- **Test scenarios**: this directory's [`test-scenarios/`](./test-scenarios/) — every scenario is locally runnable.

## How to use this plan

- **Rehearse first**: run `test-scenarios/00-environment-setup.md` once on the laptop you'll present from, *before* finalizing slide bullets. Real failures here surface gaps in claims.
- **Pre-record fallbacks**: each test scenario marked `LIVE DEMO CANDIDATE` should have a recorded fallback (asciinema or screen capture).
- **Cut for time**: the deck has slack — cuts should target slides 18, 19 (API fuzzing tools) and 24 (AI vuln research at perimeter) for the shortest version.
- **Extended version**: if you have 90 minutes, add slides 29-31 (Caido vs Burp deep dive, Hadrian template authoring walkthrough, WAFFLED-class parsing-discrepancy demo).

## Tracking

Slide-to-source mapping is in [`slides.md`](./slides.md). Every factual claim is linked to a source file in this repo. The audience-question-likely-to-be-asked sheet is at the bottom of `slides.md`.
