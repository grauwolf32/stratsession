# Seclab Taskflow Agent — code-level analysis

GitHub Security Lab's Seclab Taskflow Agent is a Typer-based Python CLI that wraps the OpenAI Agents SDK and drives multi-step LLM workflows whose entire shape — agents, tools, model bindings, prompts — is declared in a five-document YAML grammar.

## 1. Architecture overview

The CLI entry is `seclab_taskflow_agent/__main__.py:25-28`, which loads `.env` then dispatches to a Typer app defined in `seclab_taskflow_agent/cli.py:28-33`. The single `main` command (`cli.py:80-171`) wires up logging, parses `-p/-t/-l/-g/--resume` flags, and then `asyncio.run`s `runner.run_main` (`cli.py:156`).

`run_main` (`runner.py:448-733`) is the orchestrator: it instantiates `AvailableTools` (the YAML registry), resolves a `TaskflowDocument`, creates or resumes a `TaskflowSession`, then iterates the task list. Each task is executed by `deploy_task_agents` (`runner.py:241-446`), which builds MCP servers, creates a `TaskAgent`, and streams output from the OpenAI Agents SDK `Runner` via `agent.run_streamed` (`agent.py:216-218`).

The `TaskAgent` wrapper (`agent.py:141-218`) constructs an `AsyncOpenAI` client with the right `base_url`/`api_key`/default headers (`agent.py:181-185`), then selects either `OpenAIResponsesModel` or `OpenAIChatCompletionsModel` (`agent.py:196-199`) and assembles an `agents.Agent` with `mcp_servers`, `handoffs`, `model_settings`, and `hooks` (`agent.py:201-210`). Provider-specific endpoint behaviour (Copilot, GitHub Models, OpenAI, AWF proxy) lives in `capi.py:44-174`.

## 2. Module / package layout

`src/seclab_taskflow_agent/` is the package root. Notable modules:
- `cli.py` — Typer CLI shell.
- `runner.py` — the 733-line execution engine.
- `agent.py` — `TaskAgent`, `TaskRunHooks`, `TaskAgentHooks`.
- `models.py` — Pydantic grammar models.
- `available_tools.py` — YAML loader/cache/validator.
- `mcp_lifecycle.py`, `mcp_transport.py`, `mcp_utils.py`, `mcp_prompt.py` — MCP plumbing.
- `template_utils.py`, `env_utils.py` — Jinja2 rendering and env handling.
- `session.py` — checkpoint/resume persistence.
- `capi.py` — provider abstraction.
- `mcp_servers/{codeql,echo,logbook,memcache}/` — bundled in-tree MCP server implementations.
- `toolboxes/` and `personalities/` — packaged YAML configs.

## 3. YAML grammar (the core design decision)

Every YAML file carries a discriminator header `seclab-taskflow-agent: {version, filetype}` (`models.py:43-68`) and `filetype` selects which Pydantic model parses the rest. The five types are mapped at `models.py:222-228`:

```python
DOCUMENT_MODELS = {
    "taskflow": TaskflowDocument,
    "personality": PersonalityDocument,
    "toolbox": ToolboxDocument,
    "model_config": ModelConfigDocument,
    "prompt": PromptDocument,
}
```

Files are looked up by *dotted module path* (e.g. `seclab_taskflow_agent.toolboxes.codeql`) via `importlib.resources.files(package).joinpath(filename+".yaml")` (`available_tools.py:117-124`), then `yaml.safe_load`ed, header-validated, dispatched to the right Pydantic class (`available_tools.py:127-152`), and cached. **YAML modules can live in *any* installed Python package**, not just the project tree — a real plugin model.

A `TaskflowDocument` (`models.py:123-152`) declares globals, a `model_config` reference (aliased because `model_config` collides with Pydantic's `ConfigDict`, see `models.py:144`), and an ordered `taskflow:` list of `TaskWrapper`s each containing a `TaskDefinition` (`models.py:75-110`). The latter is the heart of the grammar — fields like `agents`, `user_prompt`, `run`, `toolboxes`, `model`, `model_settings`, `must_complete`, `headless`, `repeat_prompt`, `exclude_from_context`, `blocked_tools`, `env`, `inputs`, `max_steps`, `uses`, `async`, `async_limit`. A `model_validator` enforces that `run` (shell) and `user_prompt` (LLM) are mutually exclusive (`models.py:106-110`).

Prompt strings are Jinja2-rendered with a custom `PromptLoader` (`template_utils.py:19-56`) so a `user_prompt:` can `{% include 'examples.prompts.example_prompt' %}` another `PromptDocument`, and `{{ env('VAR') }}`, `{{ globals.x }}`, `{{ inputs.y }}`, `{{ result }}` are resolved with `StrictUndefined` (`template_utils.py:84-112`).

## 4. Toolbox abstraction

A toolbox is a YAML document (`ToolboxDocument`, `models.py:182-191`) that binds an MCP server to the agent. Its key field is `server_params:` (`ServerParams`, `models.py:166-179`), which carries `kind` (`stdio`, `sse`, or `streamable`), `command`/`args`/`env` for spawn-based servers, `url`/`headers`/`optional_headers` for HTTP servers, and `reconnecting:` to opt into the workaround wrapper. It also carries:
- `confirm:` — tool names that require interactive y/n approval before execution (`mcp_utils.py:100-117`). The `memcache` toolbox uses this to guard `memcache_clear_cache` (`toolboxes/memcache.yaml:18-20`).
- `server_prompt:` — markdown text appended to the agent's system prompt (e.g. the CodeQL toolbox uses ~80 lines explaining language acronyms and the `file://path:start:col:end:col` URI scheme — `toolboxes/codeql.yaml:21-79`).

Resolution into MCP client params happens in `mcp_client_params` (`mcp_utils.py:140-238`): per-kind branches build a dict, call `swap_env` to expand `{{ env('…') }}` references in env-vars/headers/args, and inherit proxy env vars (`mcp_utils.py:181-184`). Tool names from each MCP server are namespace-prefixed with a 12-char SHA-256 of the toolbox name to stay under OpenAI's 64-char limit (`mcp_utils.py:48-59`, `90-98`).

Shell-command "tools" are not MCP at all — they're tasks with a `run:` field that the runner executes directly via `shell_tool_call` (`shell_utils.py:39-44`, called from `runner.py:589-594`), and the stdout is appended to `last_mcp_tool_results` so subsequent `repeat_prompt` tasks can iterate over it.

## 5. MCP wiring

`build_mcp_servers` (`mcp_lifecycle.py:44-123`) is the dispatcher. Per `kind`:
- **`stdio`** → either `MCPServerStdio` (from the OpenAI Agents SDK at `agents.mcp`) or `ReconnectingMCPServerStdio` if `reconnecting: true` (`mcp_lifecycle.py:73-88`). The reconnecting variant (`mcp_transport.py:273-313`) connects-then-disconnects on every `call_tool`/`list_tools`, working around a documented FastMCP 1.0 stdio I/O bug.
- **`sse`** → `MCPServerSse` (`mcp_lifecycle.py:89-95`).
- **`streamable`** → `MCPServerStreamableHttp` (`mcp_lifecycle.py:96-117`). If the toolbox also has a `command`, a `StreamableMCPThread` (`mcp_transport.py:57-221`) launches the local server as a `subprocess.Popen`, captures stdout/stderr via callback threads, and exposes `async_wait_for_connection` which polls the TCP port until it accepts connections (`mcp_transport.py:95-123`).

Each server is wrapped in `MCPNamespaceWrap` (`mcp_utils.py:62-134`) for prefix-mangling and confirm-gating, then handed off to `mcp_session_task` (`mcp_lifecycle.py:126-167`) — a long-running background coroutine that connects all servers, signals via `asyncio.Event`, waits for cleanup, then tears them down in reverse order with a 5-second timeout.

Static tool blocking uses `create_static_tool_filter` from `agents.mcp` (`mcp_lifecycle.py:61`), populated from the task's `blocked_tools:` list.

## 6. Agent execution loop

The runner's per-task loop (`runner.py:532-728`):

1. **Resolves `uses:`** — `_merge_reusable_task` (`runner.py:87-113`) merges parent defaults from another taskflow with current-task overrides via `model_dump(by_alias=True, exclude_defaults=True)`.
2. **Resolves the model** — `_resolve_task_model` (`runner.py:116-159`) looks up the logical model name in the model_config's `models:` dict, extracts engine keys (`api_type`, `endpoint`, `token`) out of `model_settings`, then layers task-level overrides on top.
3. **Renders the prompt** — `render_template` (`template_utils.py:115-167`) under a `TmpEnv` context manager that temporarily sets the task's `env:` dict (`env_utils.py:55-83`).
4. **Constructs the agent set** — `deploy_task_agents` (`runner.py:241-446`) builds MCP servers, then a primary `TaskAgent` plus one handoff `TaskAgent` per additional `agents:` entry. The system prompt is assembled by `mcp_system_prompt` (`mcp_prompt.py:15-105`), which concatenates the personality `personality:` + per-server `server_prompt:`s + a hardcoded `important_guidelines` list (`runner.py:325-330`) + the personality `task:`. When there are handoffs, the prompt is further wrapped by `prompt_with_handoff_instructions` (`runner.py:340/372`).
5. **Streams execution** — the inner `_run_streamed` coroutine (`runner.py:388-413`) calls `agent0.run_streamed(prompt, max_turns=max_turns)`, streams `ResponseTextDeltaEvent`s to the console, and retries on `APITimeoutError` (5 retries) / `RateLimitError` (exponential backoff capped at 120s).

The runner injects `TaskRunHooks` and `TaskAgentHooks` (`agent.py:45-138`) so that on every tool call result the runner appends to `last_mcp_tool_results` (`runner.py:470-472`) — the data pipe between tasks.

## 7. Multi-step taskflow

Persistence is `TaskflowSession` (`session.py:45-136`), a Pydantic model written to `_data_dir()/sessions/<id>.json` after every task. It records `completed_tasks` and crucially `last_tool_results` so resumed runs can re-feed `repeat_prompt` iterators. The resume path lives in `runner.py:491-502` and `record_task` is called at `runner.py:723-728`. On any retryable network failure (`APIConnectionError`, `APITimeoutError`, etc.) the task is retried up to `TASK_RETRY_LIMIT=3` with linear backoff (`runner.py:674-696`); otherwise the session is marked failed and the user is told to resume with `--resume <id>`.

Inter-task data flow runs on three rails: (a) `last_mcp_tool_results` shared list (LIFO consumed by `repeat_prompt`), (b) the global variables dict (file defaults + `-g KEY=VALUE` overrides, `runner.py:508-510`), and (c) the persistent MCP `memcache` toolbox, which is the recommended way for agents to write structured notes that survive across tasks.

`repeat_prompt:` (`runner.py:191-238`) parses the last tool result as JSON, treats it as iterable, and renders the task's prompt once per element with `{{ result }}` bound. With `async: true` and `async_limit:` (`runner.py:602`, `654-655`) those rendered prompts run concurrently behind an `asyncio.Semaphore`.

Handoffs work through the OpenAI Agents SDK's native handoff mechanism: the first entry in `agents:` is primary and the rest become `handoffs=[…]` on the primary Agent (`runner.py:333-383`).

## 8. CodeQL MCP integration

The CodeQL toolbox (`src/seclab_taskflow_agent/toolboxes/codeql.yaml`) is a `streamable` MCP server pointing at `http://localhost:9999/mcp` with `command: python -m seclab_taskflow_agent.mcp_servers.codeql.mcp_server` (lines 9-13), so the framework auto-spawns the server in a `StreamableMCPThread`. Required env vars `CODEQL_DBS_BASE_PATH` and `CODEQL_CLI` are expanded via `swap_env` (`toolboxes/codeql.yaml:14-20`).

The server itself (`mcp_servers/codeql/mcp_server.py`) is a FastMCP 2.0 instance (`mcp_server.py:25`) exposing ten `@mcp.tool()`-decorated functions: `get_file_contents`, `list_source_files`, `search_in_source_code`, `definition_location_for_function`, `declaration_location_for_variable`, `statement_location`, `call_graph_to`, `call_graph_from`, `call_graph_from_to`, `list_functions` (`mcp_server.py:125-257`). All graph/location tools delegate to `_run_query` (`mcp_server.py:101-122`), which loads a parameterised `.ql` file from `mcp_servers/codeql/queries/mcp-{cpp,js}/…` based on a per-language dispatch table (`mcp_server.py:30-50`), runs it through `codeql` CLI via `client.run_query`, and CSV-parses the results into JSON. The transport is `mcp.run(transport="http", host="127.0.0.1", port=9999)` (`mcp_server.py:261`).

## 9. What's genuinely novel at the code level

The grammar-driven composition is the standout: a single Pydantic-validated YAML scheme (`models.py:222-228`) lets an entire LLM workflow — agents, handoffs, MCP toolboxes with bespoke `server_prompt` paragraphs, model bindings with per-model API type/endpoint/token, prompt includes, shell steps interleaved with LLM steps, and `repeat_prompt` iteration — be declared without code. The dotted-module YAML loader (`available_tools.py:117-124`) turns any installed Python package into a plugin source for personalities/toolboxes/taskflows. And the `ReconnectingMCPServerStdio` wrapper (`mcp_transport.py:273-313`) plus the `StreamableMCPThread` lifecycle (`mcp_transport.py:57-221`) bundled with `TaskflowSession` checkpoint/resume (`session.py:45-136`) make this a production-leaning take on long-running MCP-backed agent orchestration rather than a thin SDK demo.
