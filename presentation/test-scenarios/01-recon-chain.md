# 01 · Modern recon chain — ProjectDiscovery suite + Uncover

**Slide reference**: 6, 7 (live demo candidate) · **Estimated time**: 10-20 minutes · **Prerequisites**: [`00-environment-setup.md`](./00-environment-setup.md)

## Goal

Demonstrate the end-to-end ProjectDiscovery + Uncover recon chain: subdomain enumeration → alive-host probing → port scan → web crawl → search-engine-driven discovery. Output should be a structured map of an external attack surface.

## Tools used

| Tool | Role | Submodule |
|---|---|---|
| `subfinder` | Passive subdomain enumeration | [`../../sources/perimeter/subfinder`](../../sources/perimeter/subfinder) |
| `httpx` | HTTP probing + tech fingerprint | [`../../sources/perimeter/httpx`](../../sources/perimeter/httpx) |
| `naabu` | Port scanner | [`../../sources/perimeter/naabu`](../../sources/perimeter/naabu) |
| `katana` | Modern crawler | [`../../sources/perimeter/katana`](../../sources/perimeter/katana) |
| `uncover` | Multi-search-engine recon | [`../../sources/perimeter/uncover`](../../sources/perimeter/uncover) |

## Target selection

For the demo, you have two safe options:

1. **`example.com`** — bland, no real attack surface, useful for "tools-run-cleanly" demo.
2. **`scanme.nmap.org`** — Nmap's official scan-me target (allowed for scan testing).

**Do not run this scenario against any domain you don't own or have explicit written authorization for.** Even passive recon (subfinder, uncover) is logged by data providers.

For the rest of this scenario, we use `TARGET=scanme.nmap.org` (substitute as needed).

## Scenario A — Full chain demo (10 minutes)

```bash
export TARGET=scanme.nmap.org

# Step 1 — passive subdomain enumeration
subfinder -d "$TARGET" -silent > subdomains.txt
wc -l subdomains.txt    # how many subdomains discovered

# Step 2 — which are actually alive + tech stack
cat subdomains.txt | httpx -silent -tech-detect -title -status-code \
  -threads 50 -o alive.txt
cat alive.txt

# Step 3 — port scan on alive hosts (top 1000 ports)
cat alive.txt | awk '{print $1}' | sed 's|https\?://||' | naabu -silent \
  -top-ports 1000 -o open-ports.txt
cat open-ports.txt

# Step 4 — crawl one of the web targets
katana -u "https://$TARGET" -d 3 -silent -o crawled-urls.txt
wc -l crawled-urls.txt
head -20 crawled-urls.txt
```

**Expected output (rough)**:
- subdomains.txt: 0-5 lines (scanme is minimal)
- alive.txt: 1-2 lines (one or two web endpoints respond)
- open-ports.txt: 2-5 lines (22, 80, possibly 443)
- crawled-urls.txt: 10-50 URLs

The point isn't quantity — it's that **a one-line bash pipe produces a structured attack-surface map** that would have taken hours with traditional tools.

## Scenario B — Uncover (search-engine driven)

`uncover` queries Shodan / Censys / Fofa / Quake / Hunter as a unified CLI. You need API keys for at least one of these.

```bash
# Configure API keys (one is enough)
mkdir -p ~/.config/uncover/
cat > ~/.config/uncover/provider-config.yaml <<'EOF'
shodan:
  - YOUR_SHODAN_API_KEY
censys:
  - YOUR_CENSYS_API_ID:YOUR_CENSYS_API_SECRET
EOF
chmod 600 ~/.config/uncover/provider-config.yaml

# Find Apache servers reachable from internet (toy example)
uncover -q 'apache "2.4.49"' -e shodan -limit 10 -silent

# Find specific exposed admin panels (filtered query)
uncover -q 'http.title:"admin login"' -e censys -limit 20 -silent
```

**Why this is novel**: previously you'd open each provider's web UI separately and copy-paste results. `uncover` makes search-engine recon scriptable and pipeable.

```bash
# Pipe uncover into the rest of the chain
uncover -q 'org:"Your Company Name"' -e shodan -limit 50 -silent | \
  httpx -silent -tech-detect -title | \
  tee company-perimeter.txt
```

## Scenario C — Live demo (3 minutes, on-stage)

For slide 7, a tight live demo script:

```bash
# Terminal 1 — the demo
clear
echo "Discovering attack surface for scanme.nmap.org…"
subfinder -d scanme.nmap.org -silent | \
  httpx -silent -tech-detect -title -status-code | \
  tee /tmp/demo-output.txt
echo "Done."
```

Expected on-screen output (in ~10 seconds):
```
https://scanme.nmap.org [200] [Nmap Project] [nginx, OpenSSH]
```

Talking points during the live demo:
1. "This is what 2026 perimeter recon looks like — one bash pipe, three Go tools."
2. "subfinder hits ~30 passive data sources" → "httpx confirms which are live + fingerprints them" → "in production this output feeds the next tool."
3. "Notice no API keys for this part — passive sources only."

## Failure modes and recovery

| Symptom | Cause | Fix |
|---|---|---|
| `subfinder` returns 0 results | Hitting rate limits on passive sources | Wait 60s + retry; or add API keys for Chaos/SecurityTrails |
| `httpx` hangs | Some hosts very slow | Add `-timeout 5` |
| `naabu` fails with permission error | Needs CAP_NET_RAW for syn scan | Use `-sn` or `-c 25` for connect scan instead |
| `katana` finds 0 URLs | Target is heavy-JS SPA | Add `-headless -system-chrome` (requires Chrome installed) |
| `uncover` returns 401 | API key wrong / missing | Check `~/.config/uncover/provider-config.yaml` perms (600) |

## Sources for slides

- **Tool repos**: all under [`../../sources/perimeter/`](../../sources/perimeter/) — pinned to recent versions.
- **Practitioner content**: [`../../blogs/oss-usage-case-studies.md`](../../blogs/oss-usage-case-studies.md) §"Nuclei at mass-scale" includes the chain pattern.
- **Conference**: DEF CON 33 Recon Village — [`../../conferences/defcon-33.md`](../../conferences/defcon-33.md) §"Recon Village".

## Pre-recorded fallback

If the live demo fails on stage, the deck should have an asciinema recording linked. To produce one before the talk:

```bash
asciinema rec /tmp/recon-chain.cast -c "subfinder -d scanme.nmap.org -silent | httpx -silent -tech-detect"
# Upload to asciinema.org and embed link in the slide
```
