# Mem0 MCP Server

[![PyPI version](https://img.shields.io/pypi/v/mem0-mcp-server.svg)](https://pypi.org/project/mem0-mcp-server/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`mem0-mcp-server` wraps the official [Mem0](https://mem0.ai) Memory API as a Model Context Protocol (MCP) server so any MCP-compatible client (Claude Desktop, Cursor, custom agents) can add, search, update, and delete long-term memories.

### Start Here

**Prerequisites (once per shell)**

```bash
export MEM0_API_KEY="sk_mem0_..."          # required
export MEM0_DEFAULT_USER_ID="your-handle"   # optional, default mem0-mcp
export OPENAI_API_KEY="sk-openai_..."      # only needed for the agent demo (Pydantic AI)
```

| Mode | Install | Start Server | Config for clients | Quick test |
| --- | --- | --- | --- | --- |
| Local stdio (CLI) | `pip install mem0-mcp-server` or clone + `pip install -e .` | `mem0-mcp-server` (or `uvx mem0-mcp-server`) | `example/config.json` (default) | `python example/pydantic_ai_repl.py` (agent example) |
| Smithery HTTP (CLI/hosted) | `pip install "mem0-mcp-server[smithery]"` | `uv run smithery dev` (or `playground`) | copy `example/config.json`, switch to HTTP entry | Same agent REPL with custom config |
| Docker HTTP | `docker build -t mem0-mcp-server .` | `docker run --rm -e MEM0_API_KEY=… -p 8081:8081 mem0-mcp-server` | `example/docker-config.json` | Set `MEM0_MCP_CONFIG_PATH` to the docker config + run the agent REPL |

See `LOCAL_TESTING.md` for a full walkthrough of all three scenarios.

## Quick Start

```bash
pip install mem0-mcp-server
mem0-mcp-server             # or python -m mem0_mcp_server.server
```

Or skip installing system-wide:

```bash
uvx mem0-mcp-server         # pulls the published package via uv
```

To try the bundled agent example (built with Pydantic AI; repo checkout required—the REPL
lives under `example/` in this repo, not the PyPI wheel):

```bash
pip install -e ".[smithery]"      # installs deps + smithery extra
python example/pydantic_ai_repl.py  # talks to the local stdio server
```
Make sure the prerequisites section above was followed (`MEM0_API_KEY` and
`OPENAI_API_KEY` must be exported before running the REPL).

### Optional: HTTP / Smithery / Docker

To run the HTTP transport with Smithery:

1. `pip install -e ".[smithery]"` (or `pip install "mem0-mcp-server[smithery]"`).
2. Ensure `MEM0_API_KEY` (and optional `MEM0_DEFAULT_USER_ID`) are exported.
3. `uv run smithery dev` for a local endpoint (`http://127.0.0.1:8081/mcp`).
4. Optional: `uv run smithery playground` to open an ngrok tunnel + Smithery web UI.
5. Test by pointing `MEM0_MCP_CONFIG_PATH` to an HTTP config (see “Reusing configs”).
6. Hosted deploy: push to GitHub, connect at [smithery.ai](https://smithery.ai/new), click Deploy (Smithery imports `mem0_mcp_server.server:create_server`).

To containerize the server (for Smithery deployments or any other host), build the included `Dockerfile`:

```bash
docker build -t mem0-mcp-server .
# run the HTTP endpoint (still need MEM0_API_KEY)
docker run --rm -e MEM0_API_KEY=sk_mem0_... -p 8081:8081 mem0-mcp-server
```

Then point clients (or the agent REPL) at the container via `example/docker-config.json`:

```bash
export MEM0_MCP_CONFIG_PATH="$PWD/example/docker-config.json"
python example/pydantic_ai_repl.py
```

Troubleshooting:
- The container must be running **before** HTTP clients connect, and it must
  receive `MEM0_API_KEY` (and optional `MEM0_DEFAULT_USER_ID`) via `-e`.
- The first `docker build` downloads dependencies; reruns use cache.

### Reusing Config Files in Other MCP Clients

Both `example/config.json` (local stdio) and `example/docker-config.json`
(HTTP) are standard MCP configs. Copy them into any client (Claude Desktop,
Cursor, custom apps) and tweak:

- **StdIO**: adjust `command`/`args` (e.g., switch from `python -m ...` to
  `uvx mem0-mcp-server`).
- **HTTP**: change `url` to your Smithery endpoint or another host.
- Use `MEM0_MCP_CONFIG_PATH`/`MEM0_MCP_CONFIG_SERVER` to make the agent REPL (built with Pydantic AI)
  or any other client pick a specific entry.

You should immediately see `Starting Mem0 MCP server (default user=...)`, after which the server waits on stdio for whatever MCP host you connect.

### How the config files work

- `src/mem0_mcp_server/config.json` is the base template. Every MCP host looks at the `mcpServers` map, runs the listed `command` + `args`, and fills in `${VAR}` placeholders from your environment.
- **Local stdio example (`example/config.json`)**: keep the `command`/`args` section so it launches `python -m mem0_mcp_server.server` (swap to `uvx mem0-mcp-server` if you prefer). Set `MEM0_API_KEY` and optionally `MEM0_DEFAULT_USER_ID`. Nothing else changes.
- **Smithery HTTP example**: duplicate `example/config.json`, change the entry to `{ "type": "http", "url": "https://your-smithery-host/mcp" }`, and point `MEM0_MCP_CONFIG_PATH` to that file. The agent REPL will call Smithery instead of starting a local binary.
- **Docker example (`example/docker-config.json`)**: keep `"type": "http"` and set `url` to wherever your container exposes `/mcp` (e.g., `http://localhost:8081/mcp` or `http://host.docker.internal:8081/mcp`).
- Switch between these configs by exporting `MEM0_MCP_CONFIG_PATH=/full/path/to/config.json` before running the agent example or any other MCP client.

### Environment Variables
- `MEM0_API_KEY` (required) – Mem0 platform API key.
- `MEM0_DEFAULT_USER_ID` (optional) – default `user_id` injected into filters and write requests (defaults to `mem0-mcp`).
- `MEM0_MCP_AGENT_MODEL` (optional, example helper only) – default LLM for the bundled agent example (implemented with Pydantic AI).

### Agent example (Pydantic AI)

Use the standalone agent example under `example/` for a local REPL (powered by Pydantic AI) that talks to your Mem0 MCP server:

```bash
pip install -e ".[smithery]"          # if you're developing locally
export MEM0_API_KEY="sk_mem0_..."
export OPENAI_API_KEY="sk-openai-..."  # or another supported provider
python example/pydantic_ai_repl.py
```

This script launches `mem0_mcp_server.server` via the bundled `example/config.json`, then connects an agent (“Mem0Guide”) implemented with Pydantic AI over stdio. Use it to test your API key with prompts like “search memories for favorite food.” The agent now inherits `MEM0_DEFAULT_USER_ID` from your environment/session config (fallback `mem0-mcp`). Change the config path or server key via `MEM0_MCP_CONFIG_PATH` / `MEM0_MCP_CONFIG_SERVER` to point at Smithery or Docker instead. For a full walkthrough see `LOCAL_TESTING.md`.

### FAQ / Troubleshooting

- **I see `RuntimeWarning: 'mem0_mcp_server.server' found in sys.modules…`** –
  harmless when running the agent REPL (Pydantic AI); Python just warns when it reloads the
  same module in a subprocess.
- **`session_config not found in request scope` warning** – expected when
  running outside Smithery; the server falls back to env vars.
- **Docker clients can’t connect (`ConnectError`)** – ensure `docker run ...`
  is running and that you forwarded `-p 8081:8081`; point configs to
  `http://localhost:8081/mcp`.
- **Smithery CLI says “server reference not found”** – reinstall the project
  with the `[smithery]` extra and ensure `[tool.smithery] server =
  "mem0_mcp_server.server:create_server"` is present in `pyproject.toml`.

### Using with other MCP hosts

- **Claude Desktop / Cursor / generic hosts**: set their MCP entry to run `uvx mem0-mcp-server` (or the installed `mem0-mcp-server` binary). No additional glue code is needed because the server speaks stdio MCP by default.
- **Custom tooling**: spawn `python -m mem0_mcp_server.server` inside your agent stack and exchange MCP messages over stdio.

Example `claude_desktop_config.json` snippet:

```json
{
  "mcpServers": {
    "mem0": {
      "command": "uvx",
      "args": ["mem0-mcp-server"],
      "env": {
        "MEM0_API_KEY": "sk_mem0_...",
        "MEM0_DEFAULT_USER_ID": "your-handle"
      }
    }
  }
}
```

For other hosts (Cursor, Smithery, custom bridges) the idea is identical: call `uvx mem0-mcp-server` and pass the same environment block, or invoke the `mem0-mcp-server` binary directly if the package is preinstalled.

### Bundled MCP config

The package includes `src/mem0_mcp_server/config.json`, a ready-to-use template that matches the snippet above and supports `${VAR}` expansion (handled by `load_mcp_servers`). Point Claude Desktop (or any host) at the file verbatim, or copy/paste it into your own config store. The same file powers the examples under `example/`, so every client—GUI or CLI—can share a single authoritative configuration.

## MCP Tools Exposed

| Tool | Description |
| --- | --- |
| `add_memory` | Save text or conversation history (or explicit message objects) for a user/agent. |
| `search_memories` | Semantic search across existing memories (filters + limit supported). |
| `get_memories` | List memories with structured filters and pagination. |
| `get_memory` | Retrieve one memory by its `memory_id`. |
| `update_memory` | Overwrite a memory’s text once the user confirms the `memory_id`. |
| `delete_memory` | Delete a single memory by `memory_id`. |
| `delete_all_memories` | Bulk delete all memories in the confirmed scope (user/agent/app/run). |
| `delete_entities` | Delete a user/agent/app/run entity (and its memories). |
| `list_entities` | Enumerate users/agents/apps/runs stored in Mem0. |

All responses are JSON strings returned directly from the Mem0 API via the official `mem0ai` SDK.

## Development

```bash
uv sync --python 3.11                  # optional, installs dev extras and lockfile
uv run --from . mem0-mcp-server        # run local checkout via uvx
```

## License
MIT
