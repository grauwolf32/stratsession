# 00 · Environment setup

Bring up the lab infrastructure that the rest of the test scenarios target. **Run this once before any other scenario.**

## What you'll deploy

```
┌───────────────────────────────────────────────────────────────┐
│ Docker network: stratlab (172.30.0.0/16)                       │
│                                                                │
│ ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│ │ OWASP crAPI  │  │ Juice Shop   │  │ Coraza + CRS WAF    │    │
│ │ 172.30.0.10  │  │ 172.30.0.20  │  │ 172.30.0.30         │    │
│ │ :8888, :8025 │  │ :3000        │  │ :80 → upstream      │    │
│ └──────────────┘  └──────────────┘  └─────────────────────┘    │
│                                                                │
│ ┌──────────────┐                                               │
│ │ Akto         │  (deployed in scenario 06; not started here) │
│ │ 172.30.0.40  │                                               │
│ └──────────────┘                                               │
└────────────────────────────────────────────────────────────────┘
```

## Requirements

- **Disk**: ≥30 GB free (Akto, crAPI, Juice Shop, and tool databases).
- **RAM**: ≥16 GB (Buttercup alone needs 16 GB minimum if you run scenario 07; without Buttercup, 8 GB is enough).
- **Docker**: 25.x+ with Compose v2.
- **Internet**: tools fetch templates / vuln DBs / LLM responses at runtime.

## Step 1 — Clone the lab

```bash
# repo root
cd /home/ruslan/src/stratsession

# verify submodules are populated
git submodule status | grep perimeter | wc -l   # should print 15
git submodule status | grep appsec | wc -l      # should print 17
```

If counts are wrong: `git submodule update --init --recursive`.

## Step 2 — Bring up the vulnerable targets

### crAPI (primary target)

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/crapi
cd deploy/docker
docker compose pull
docker compose -f docker-compose.yml --profile traefik up -d
```

Wait for ~2 minutes (microservices take time to come up). Verify:

```bash
curl -s http://localhost:8888 | head -5            # web UI
curl -s http://localhost:8888/identity/api/v2/      # API surface
```

crAPI exposes:
- Web UI: `http://localhost:8888`
- Mail UI (catch test emails): `http://localhost:8025`
- Identity API: `:8888/identity/api/v2/`
- Workshop API: `:8888/workshop/api/`
- Community API: `:8888/community/api/v2/`

Create a test user in the UI before running API tests (the API discovery scenarios need an authenticated session). Note the bearer token from the browser's DevTools → Network tab.

### OWASP Juice Shop (secondary target — for Caido DAST scenario)

```bash
docker run -d --rm -p 3000:3000 --name juiceshop \
  --network stratlab \
  bkimminich/juice-shop:latest
```

Verify: `curl -s http://localhost:3000 | grep -i juice` returns something.

Create the shared network first if it doesn't exist:

```bash
docker network create --subnet 172.30.0.0/16 stratlab 2>/dev/null || true
```

## Step 3 — Install tools that need host installation

Most submodule tools are runnable directly from the cloned source. A few need a host install for IDE / GUI usage:

### Caido (desktop app)

Download from https://caido.io (free Community Edition):
- macOS: `brew install --cask caido` or download DMG
- Linux: AppImage from caido.io/releases
- Windows: installer from caido.io

Caido CLI (for headless/CI usage, optional):
```bash
# install from the cloned source (Rust toolchain required)
cd /home/ruslan/src/stratsession/sources/perimeter/caido
cargo build --release
# binary: ./target/release/caido-cli
```

### ProjectDiscovery tools (Go)

If you have Go installed, fastest path is:

```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/projectdiscovery/uncover/cmd/uncover@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

Or run from cloned sources:
```bash
cd /home/ruslan/src/stratsession/sources/perimeter/nuclei
go build -o /tmp/nuclei ./cmd/nuclei
/tmp/nuclei -version
```

Nuclei needs templates on first run:
```bash
nuclei -update-templates -update-template-dir ~/.local/share/nuclei-templates
```

### Python tools (Schemathesis, Akto cli helpers)

```bash
# isolated venv
python -m venv ~/.venvs/stratlab
source ~/.venvs/stratlab/bin/activate

# from cloned source
pip install -e /home/ruslan/src/stratsession/sources/perimeter/schemathesis
# verify
schemathesis --version
```

### Rust tools (Cherrybomb)

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/cherrybomb
cargo build --release
# binary: ./target/release/cherrybomb
```

### RESTler (Microsoft, .NET-based)

```bash
cd /home/ruslan/src/stratsession/sources/perimeter/restler-fuzzer
docker build -t restler:local -f Dockerfile .
```

### Hadrian + Vespasian (cross-listed from appsec)

```bash
cd /home/ruslan/src/stratsession/sources/appsec/vespasian
go build -o /tmp/vespasian ./cmd/vespasian

cd /home/ruslan/src/stratsession/sources/appsec/hadrian
go build -o /tmp/hadrian ./cmd/hadrian
```

## Step 4 — LLM API keys (for AI-using tools)

Several tools in scenarios 02, 04, 07 use LLMs. Set environment variables before running them:

```bash
# .env file in the repo root, NOT committed
cat > ~/.stratlab.env <<'EOF'
# Anthropic — for Hadrian planner/triage, Buttercup (one of three providers), Taskflow Agent
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI — for Hadrian planner, Nuclei AI, Buttercup
OPENAI_API_KEY=sk-...

# Optional: Google for Buttercup
GEMINI_API_KEY=...

# For Hadrian's `--planner-provider ollama` (no API key, just host)
OLLAMA_HOST=http://localhost:11434
EOF

source ~/.stratlab.env
```

## Step 5 — Verify everything works

```bash
cat > /tmp/verify-stratlab.sh <<'EOF'
#!/bin/bash
set -e
echo "=== Docker ==="
docker version > /dev/null && echo "OK"

echo "=== crAPI web UI ==="
curl -sf http://localhost:8888 > /dev/null && echo "OK"

echo "=== crAPI mail UI ==="
curl -sf http://localhost:8025 > /dev/null && echo "OK"

echo "=== Juice Shop ==="
curl -sf http://localhost:3000 > /dev/null && echo "OK"

echo "=== Submodules ==="
cd /home/ruslan/src/stratsession
test "$(git submodule status | grep perimeter | wc -l)" = "15" && echo "perimeter: 15 OK"
test "$(git submodule status | grep appsec | wc -l)" = "17" && echo "appsec: 17 OK"

echo "=== Tools (subset) ==="
for t in nuclei subfinder httpx katana naabu schemathesis cherrybomb; do
  command -v $t > /dev/null && echo "$t: OK" || echo "$t: MISSING"
done
EOF
chmod +x /tmp/verify-stratlab.sh
/tmp/verify-stratlab.sh
```

Expected output: all `OK`. Any `MISSING` lines indicate a tool not on PATH — re-run the install step above for that tool, or invoke it from its cloned-source path.

## Teardown

```bash
# stop crAPI
cd /home/ruslan/src/stratsession/sources/perimeter/crapi/deploy/docker
docker compose down -v

# stop juice shop
docker stop juiceshop 2>/dev/null

# tear down network (last step)
docker network rm stratlab 2>/dev/null

# nuke all unused images/volumes (optional, frees disk)
docker system prune -a -f --volumes
```

## Known gotchas

- **crAPI's docker-compose has multiple profiles**: `traefik` for the unified reverse-proxy view (recommended for demos), or the default profile that exposes each microservice separately.
- **Akto needs MongoDB Atlas or local MongoDB** — scenario 06 covers setup. Don't try to bring Akto up here; it has the heaviest infrastructure footprint of the 15 tools.
- **Buttercup needs k3d / kind for the full deployment**, not docker-compose. Scenario 07 covers it; expect 20+ minutes for first boot.
- **Vespasian's headless-Chrome SSRF protection requires `--dangerous-allow-private`** when crawling localhost. *Never* use that flag against production.

## What's next

After verifying the environment, the natural first scenario is [`01-recon-chain.md`](./01-recon-chain.md) — quickest payoff (recon tools are tiny and fast) and proves the ProjectDiscovery tools are installed correctly.
