# Defensive ops source mirrors

Git submodules of two 2026 releases that close long-standing gaps in OSS defensive tooling: a modern per-process Linux firewall and an OSS SOAR with LLM agents. See [`../../reports/defensive-ops.md`](../../reports/defensive-ops.md) for the deep-dive.

## Layout

| Path | Upstream | Layer | Note |
|---|---|---|---|
| [`littlesnitch-linux/`](./littlesnitch-linux) | https://github.com/obdev/littlesnitch-linux | Host firewall | Open-source components (eBPF kernel programs + Rust common crate + demo-runner + JS web UI) of Little Snitch for Linux by Objective Development. GPL-2.0. Full product also includes proprietary userspace not in this repo. **(new 2026)** |
| [`allama/`](./allama) | https://github.com/digitranslab/allama | SOC orchestration | Open-source SOAR with visual workflow builder, autonomous LLM agents (OpenAI / Anthropic / Azure / Ollama via PydanticAI + LiteLLM), Temporal-backed durable execution, 80+ integrations. AGPL-3.0. **(new 2026)** |

## Cross-list

- **OpenSnitch** ([evilsocket/opensnitch](https://github.com/evilsocket/opensnitch)) is the mature OSS alternative to Little Snitch for Linux — fully GPL, netfilter-based, Python daemon, Qt UI. Use OpenSnitch when 100% OSS userspace matters; use Little Snitch for Linux when eBPF performance and web-UI deployment matter.
- **Falco + Stratoshark + Tetragon + Tracee** — the container-runtime defensive stack; covered in `TOOLS.md` and the conferences index. Little Snitch for Linux is the **bare-metal / VM-host** equivalent layer.
- **mquire** ([`../dfir/mquire`](../dfir/mquire)) — the post-incident forensics layer that pairs with the host-level enforcement Little Snitch for Linux provides.
- **DefectDojo** ([`../appsec/defectdojo`](../appsec/defectdojo)) — vuln-management system of record that fits naturally as a finding source for Allama workflows.

## Recent defensive tools worth knowing about (not mirrored here)

Pattern is identical — ask if you want any added:

- **[OpenSnitch](https://github.com/evilsocket/opensnitch)** — see above.
- **[Shuffle](https://github.com/Shuffle/Shuffle)** — the most mature OSS SOAR competitor; large integration catalog, own workflow runtime.
- **[StackStorm](https://github.com/StackStorm/st2)** — general event-driven automation; older and broader.
- **[TheHive](https://github.com/TheHive-Project/TheHive)** + **[Cortex](https://github.com/TheHive-Project/Cortex)** — OSS incident-response case management + analyzer framework. Pairs well with Allama.
- **[n8n](https://github.com/n8n-io/n8n)** — general workflow automation; increasingly used for SOAR-shaped tasks.
- **[Falco](https://github.com/falcosecurity/falco)** — CNCF-graduated runtime detection.
- **[Tetragon](https://github.com/cilium/tetragon)** — Cilium's eBPF security observability.

## Common operations

```bash
git submodule update --init --recursive
git submodule update --remote sources/defense/allama
git submodule deinit sources/defense/<name>
git rm sources/defense/<name>
rm -rf .git/modules/sources/defense/<name>
```
