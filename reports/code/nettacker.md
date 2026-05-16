# Nettacker — code-level analysis

## 1. Architecture overview

Single Python process with three faces: a CLI app (default), a Flask REST API (`-S`), and a static HTML/Angular Web UI served by that same Flask app. Entry point is `nettacker.py:6` which delegates to `nettacker/main.py:6`, which instantiates `Nettacker()` (a subclass of `ArgParser`) from `nettacker/core/app.py:40` and calls `.run()`. `run()` generates a scan ID, expands targets, dispatches multi-process scans, then emits HTML/JSON/CSV/text reports via `create_report()` (`nettacker/core/app.py:197-222`). For the API mode, `nettacker/api/engine.py:597-616` spawns Flask in a `multiprocessing.Process` and routes `/new/scan` (`api/engine.py:239-271`) to instantiate the same `Nettacker` class with a `SimpleNamespace` of form values, running the scan in a `Thread`. Same code path, different glue.

## 2. Module / package layout

```
nettacker/
  main.py, config.py, logger.py        # entry, config singletons, logging
  core/
    app.py                # Nettacker (orchestrator)
    arg_parser.py         # argparse + module/profile/graph loader
    module.py             # YAML module -> executable scan
    template.py           # YAML loader with `{var}` interpolation
    socks_proxy.py        # monkey-patches socket.socket
    fuzzer.py, ip.py, graph.py, messages.py
    lib/                  # per-protocol "Engine" classes
      base.py http.py ftp.py ftps.py ssh.py smb.py smtp.py smtps.py
      pop3.py pop3s.py telnet.py socket.py ssl.py
    utils/common.py       # fuzzer expansion + Cartesian product
  modules/                # YAML scan definitions
    scan/   (port.yaml, dir.yaml, subdomain.yaml, waf.yaml, …)
    brute/  (ssh.yaml, ftp.yaml, smb.yaml, telnet.yaml, …)
    vuln/   (log4j_cve_2021_44228.yaml, apache_cve_2021_41773.yaml, ~80 CVEs)
  database/
    db.py, models.py, sqlite.py, mysql.py, postgresql.py
  api/
    engine.py             # Flask app, routes, server bootstrap
    core.py, helpers.py
  lib/                    # auxiliary: icmp/, graph/, html_log/, compare_report/, payloads/
  web/static/             # index.html + Angular SPA (rendered via render_template)
```

The `nettacker/lib/payloads/` subtree holds wordlists (`passwords/top_1000_common_passwords.txt`, `wordlists/dir_wordlist.txt`) and the UA list (`User-Agents/web_browsers_user_agents.txt`, referenced from `nettacker/config.py:137`).

## 3. Module-as-YAML system (the core idea)

Every scanner — port scan, directory brute, Log4Shell, SSH brute — is just a YAML file under `nettacker/modules/{scan,brute,vuln}/`. There is **no Python** for individual modules; the loader is `nettacker/core/template.py:8-42`:

```python
def open(self):
    module_name_parts = self.name.split("_")
    action = module_name_parts[-1]            # scan / brute / vuln
    library = "_".join(module_name_parts[:-1])
    with open(Config.path.modules_dir / action / f"{library}.yaml") as f: ...
def format(self):    return self.open().format(**self.inputs)   # str.format()
def load(self):      return self.parse(yaml.safe_load(self.format()), self.inputs)
```

So the module name `ssh_brute` resolves to `modules/brute/ssh.yaml`, `format()` substitutes `{target}`, `{user_agent}`, `{url_base_path}`, and `parse()` recursively replaces any other key in the YAML whose name matches a CLI option. A module looks like (`nettacker/modules/brute/ssh.yaml:11-39`):

```yaml
payloads:
  - library: ssh                # picks engine: nettacker/core/lib/ssh.py
    steps:
      - method: brute_force     # method on SshLibrary
        host: '{target}'
        ports: [22, 2222]
        usernames: [root, admin, user, test]
        passwords:
          nettacker_fuzzer:
            input_format: '{{passwords}}'
            data:
              passwords:
                read_from_file: passwords/top_1000_common_passwords.txt
        response:
          condition_type: or
          conditions:
            successful_login:
              regex: ''
              reverse: false
```

Two interesting sub-mechanisms power this:

- **`nettacker_fuzzer`** blocks are detected by `find_repeaters()` (`nettacker/core/utils/common.py:212-227`), the named arrays are exploded with `read_from_file` callbacks (`apply_data_functions`, `common.py:303-315`) and Cartesian-producted into concrete sub-steps via `arrays_to_matrix() = itertools.product(...)` (`common.py:279-283`) and `generate_new_sub_steps()` (`common.py:201-209`). `expand_step()` (`common.py:376-382`) is the entry point. There's an interceptor mechanism (`ALLOWED_INTERCEPTORS = {"generate_and_replace_md5": ...}`, `common.py:318-320`) for transforming generated payloads.
- **`dependent_on_temp_event` / `save_to_temp_events_only`** lets a step consume an earlier step's response — used to chain a token-fetch with a token-injection (`nettacker/modules/vuln/log4j_cve_2021_44228.yaml:28` saves a Huntress token, lines 41-95 inject it into ~50 HTTP header variants). Resolution is via `BaseEngine.find_and_replace_dependent_values` (`nettacker/core/lib/base.py:60-107`), which literally `eval()`s expressions like `dependent_on_temp_event[0]['content'][0]` against the saved event dictionary — a Python expression embedded in YAML.

Response matching is fully data-driven: each step has `response.condition_type: and|or` plus per-field `regex`/`reverse` conditions (`nettacker/core/lib/http.py:45-135`) over `status_code`, `content`, `headers`, `url`, and `responsetime` (with `>= <= ==` comparisons — implemented via `exec()` at `http.py:84-90`).

## 4. Scan engine dispatch

Three-tier concurrency:

1. **Process pool**: `Nettacker.start_scan()` (`nettacker/core/app.py:230-254`) splits targets into groups by CPU-mapped "hardware usage" (`generate_target_groups` + `select_maximum_cpu_core`, `nettacker/core/utils/common.py:263-276,401-415`; `maximum = cpu_count-1`) and spawns one `multiprocess.Process` per group (the third-party `multiprocess` package, not stdlib).
2. **Thread per (target × module)**: `scan_target_group()` (`app.py:290-327`) walks the cross-product of `targets × selected_modules` and launches a `Thread` for each, throttled by `--parallel-module-scan`.
3. **Thread per sub-step**: `Module.start()` (`nettacker/core/module.py:141-199`) further fans out individual fuzzer-expanded sub-steps as threads, throttled by `--thread-per-host`, with `time.sleep(time_sleep_between_requests)` between launches.

Inside HTTP requests, `aiohttp` over `uvloop` is used: `asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())` and `asyncio.run(send_request(...))` per call (`nettacker/core/lib/http.py:20, 180`). So the architecture is process-pool > threads > asyncio for HTTP only.

Engines are dynamically imported by string at runtime: `importlib.import_module(f"nettacker.core.lib.{library.lower()}")` and `getattr(..., f"{library.capitalize()}Engine")` (`nettacker/core/module.py:156-159`). Adding a new protocol = drop a file in `core/lib/` that subclasses `BaseEngine` + `BaseLibrary` (`nettacker/core/lib/base.py:19-31`).

## 5. Database + drift detection

SQLAlchemy ORM with three tables (`nettacker/database/models.py`):

- `Report` (id, date, scan_unique_id, report_path_filename, options)
- `TempEvents` (id, date, target, module_name, scan_unique_id, event_name, port, event, data) — used for inter-step dependencies
- `HostsLog` aka `scan_events` (id, date, target, module_name, scan_unique_id, port, event, json_event) — the main findings table

SQLite path is `~/.nettacker/data/nettacker.db` (`nettacker/config.py:105, 123-125`; old `.data/` is auto-migrated, `nettacker/core/app.py:80-84`). MySQL/Postgres are alternate engines (`db_inputs()`, `nettacker/database/db.py:22-40`). For SQLite, Nettacker prefers **APSW** over SQLAlchemy when `use_apsw_for_sqlite=True` (the default, `config.py:152`) and sets `journal_mode=WAL` + `synchronous=NORMAL` via PRAGMAs (`db.py:51-66`) — explicit tuning for highly concurrent inserts from many threads/processes.

**Drift detection** is set-difference, not row diff. `create_compare_report()` (`nettacker/core/graph.py:320-402`) loads `HostsLog` rows for both `scan_id` and the user-supplied `--scan-compare` ID, keys each row as `(target, module_name, port)`, then computes:

```python
"new_targets_discovered":  curr_modules_ports - comp_modules_ports
"old_targets_not_detected": comp_modules_ports - curr_modules_ports
```

Output goes to HTML / JSON / CSV / text depending on extension. `remove_old_logs()` (`nettacker/database/db.py:178-226`) deliberately skips deleting rows whose `scan_unique_id == scan_compare_id` so the baseline survives.

## 6. Three interfaces

- **CLI**: `argparse.ArgumentParser` subclassed as `ArgParser` (`nettacker/core/arg_parser.py:27-42`). Argument groups for engine, target, method, API (`arg_parser.py:134+`). `Nettacker(ArgParser)` inherits the parser so `self.arguments` is populated in `__init__`.
- **REST API**: Flask app at `nettacker/api/engine.py:51` with ~20 routes (`api/engine.py:60-535`): `/new/scan`, `/compare/scans`, `/session/{check,set,kill}`, `/results/get{,_json,_csv,_list}`, `/logs/{get_list,get_html,get_json,get_csv,search}`. Auth via `api_key_is_valid()` (header/cookie check, `api/core.py`) plus an IP whitelist (`api_client_whitelisted_ips`). HTTPS uses either a provided cert or Werkzeug `ssl_context="adhoc"` self-signed (`api/engine.py:574-591`). The `Server:` header is monkey-patched to `"API"` to hide Werkzeug version (`api/engine.py:47`).
- **Web UI**: Same Flask process. `app = Flask(__name__, template_folder=str(Config.path.web_static_dir))` (`api/engine.py:51`) and `render_template("index.html", ...)` at `/` (`api/engine.py:194-238`). The SPA is Angular 1 + Bootstrap + D3 (`nettacker/web/static/index.html`, `nettacker/web/static/js/{angular.min.js,d3.v4.min.js,main.js}`); it consumes the same REST endpoints listed above.

## 7. Evasion knobs

All wired through CLI flags into the per-request path:

- `--user-agent` / `random_user_agent` — `nettacker/core/arg_parser.py:316-322` + `arg_parser.py:711` loads `lib/payloads/User-Agents/web_browsers_user_agents.txt` into `options.user_agents`; HTTP engine picks one per request: `sub_step["headers"]["User-Agent"] = random.choice(options["user_agents"])` (`nettacker/core/lib/http.py:165-166`).
- `-w / --time-sleep-between-requests` — `arg_parser.py:332-340`, enforced with `time.sleep(self.module_inputs["time_sleep_between_requests"])` between thread launches in `Module.start()` (`nettacker/core/module.py:191`).
- `-R / --socks-proxy` — `arg_parser.py:390-397`. Applied by **monkey-patching** the `socket` module in each scan thread: `socket.socket, socket.getaddrinfo = set_socks_proxy(options.socks_proxy)` (`nettacker/core/app.py:267`, implementation `nettacker/core/socks_proxy.py:17-41` using PySocks; SOCKS5 vs SOCKS4 chosen by URL prefix). Forces every subsequent stdlib socket call (ftp, smtp, ssh transport, raw TCP) through the proxy.
- `--retries` — `arg_parser.py:398-405`, used as a per-step retry loop in both HTTP (`nettacker/core/lib/http.py:178-184`) and the generic base engine (`nettacker/core/lib/base.py:288-293`).
- `-H / --http-header` — arbitrary headers injected into HTTP sub-steps (`nettacker/core/lib/http.py:152-159`).
- `-T / --timeout` — propagated as the `timeout` field in every YAML step.
- `--ping-before-scan` requires root because raw ICMP needs `SOCK_RAW` (`nettacker/core/app.py:165-177`).

Notably absent: no jitter, no rate-limit-aware backoff, no per-host adaptive throttling — it's static delay + static retry.

## 8. Multi-protocol

Each protocol has one file in `nettacker/core/lib/` exposing a `<Proto>Engine(BaseEngine)` and a `<Proto>Library(BaseLibrary)` pair:

| Protocol | File | Underlying library |
|---|---|---|
| HTTP/HTTPS | `core/lib/http.py:138` | `aiohttp` + `uvloop` |
| Raw TCP / port scan | `core/lib/socket.py:41` | stdlib `socket`, optional `ssl.wrap_socket` |
| FTP / FTPS | `core/lib/ftp.py:6`, `ftps.py` | `ftplib.FTP` / `FTP_TLS` |
| SSH | `core/lib/ssh.py:11` | `paramiko.SSHClient` with `Password`/`NoneAuth` strategies |
| SMB | `core/lib/smb.py` | `smb` library |
| SMTP / SMTPS | `core/lib/smtp.py`, `smtps.py` | `smtplib` |
| POP3 / POP3S | `core/lib/pop3.py`, `pop3s.py` | `poplib` |
| Telnet | `core/lib/telnet.py` | `telnetlib` |
| SSL/TLS | `core/lib/ssl.py` | stdlib `ssl` for cert inspection (used by `ssl_*_vuln` modules) |
| ICMP | `nettacker/lib/icmp/engine.py:99-194` | raw `SOCK_RAW` socket, manual checksum |
| XML-RPC (WordPress) | *(no dedicated lib)* | HTTP engine sends raw XML POSTs (e.g. `nettacker/modules/vuln/wp_xmlrpc_dos.yaml:24`) |

Service correlation: after `port_scan` runs, `Module.load()` (`nettacker/core/module.py:78-109`) reads the saved port-scan events for the target, builds `{protocol: [ports]}`, and **filters out payloads whose `library:` was not discovered on this host**, then `TemplateLoader.parse()`s the discovered ports into the surviving steps. That's the "vuln-scans-only-where-relevant" behavior.

## 9. What's genuinely novel at the code level

(a) The YAML-as-module DSL is unusually expressive for a Python scanner: the `dependent_on_temp_event` / `save_to_temp_events_only` pattern lets pure-data modules implement multi-stage exploits (token fetch → token injection) without any per-module Python, and is implemented by literally `eval()`-ing the expression in `nettacker/core/lib/base.py:79,100` against the saved-event dict — powerful but a trust boundary (modules can run arbitrary Python expressions). (b) The `nettacker_fuzzer` + `arrays_to_matrix` block (`core/utils/common.py:279-283, 367-382`) turns any combination of fuzzed fields into an `itertools.product` of concrete sub-steps before scheduling — schemas × ports × paths × passwords all explode the same way. (c) Drift detection treats `(target, module, port)` as the unit of comparison and uses Python `set` difference (`core/graph.py:352-364`), which is genuinely simple and avoids the engineering cost of row-level diffing while still surfacing what changed between runs.
