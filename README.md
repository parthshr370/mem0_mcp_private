# Mem0 MCP Server

[![PyPI version](https://img.shields.io/pypi/v/mem0-mcp-server.svg)](https://pypi.org/project/mem0-mcp-server/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`mem0-mcp-server` wraps the official [Mem0](https://mem0.ai) Memory API as a Model Context Protocol (MCP) server so any MCP-compatible client (Claude Desktop, Cursor, custom agents) can add, search, update, and delete long-term memories. Run it two ways:

1. **Local stdio (CLI)** – install from PyPI (or this repo) and launch with `uvx mem0-mcp-server`.
2. **Smithery HTTP** – install the Smithery extra and run `uv run smithery dev` or `uv run smithery playground` for an HTTP endpoint.
3. **Docker HTTP** – build the provided Docker image, run it with `docker run -e MEM0_API_KEY=… -p 8081:8081 mem0-mcp-server`, and connect via HTTP.

## Quick Start

```bash
pip install mem0-mcp-server
export MEM0_API_KEY="sk_mem0_..."
export MEM0_DEFAULT_USER_ID="your-handle"   # optional
mem0-mcp-server             # or python -m mem0_mcp_server.server
```

Or skip installing system-wide:

```bash
uvx mem0-mcp-server         # pulls the published package via uv
```

To sanity-check via the bundled Pydantic agent (repo checkout required):

```bash
pip install -e ".[smithery]"      # installs deps + smithery extra
export OPENAI_API_KEY="sk-openai-..."
python example/pydantic_ai_repl.py  # talks to the local stdio server
```

### Optional: HTTP / Smithery / Docker

Install the optional Smithery extras when you want the HTTP transport and playground CLI:

```bash
pip install "mem0-mcp-server[smithery]"
export MEM0_API_KEY="sk_mem0_..."
uv run smithery dev        # local HTTP endpoint on http://127.0.0.1:8081/mcp
uv run smithery playground # ngrok tunnel + web playground
```

To containerize the server (for Smithery deployments or any other host), build the included `Dockerfile`:

```bash
docker build -t mem0-mcp-server .
# run the HTTP endpoint (still need MEM0_API_KEY)
docker run --rm -e MEM0_API_KEY=sk_mem0_... -p 8081:8081 mem0-mcp-server
```

Point clients (or the Pydantic REPL) at the container via `example/docker-config.json`:

```bash
export MEM0_MCP_CONFIG_PATH="$PWD/example/docker-config.json"
python example/pydantic_ai_repl.py
```

You should immediately see `Starting Mem0 MCP server (default user=...)`, after which the server waits on stdio for whatever MCP host you connect.

### Environment Variables
- `MEM0_API_KEY` (required) – Mem0 platform API key.
- `MEM0_DEFAULT_USER_ID` (optional) – default `user_id` injected into filters and write requests (defaults to `mem0-mcp`).
- `MEM0_MCP_AGENT_MODEL` (optional, example helper only) – default LLM for the bundled Pydantic AI example.

### Pydantic AI example

Use the standalone example under `example/` for a local REPL that hits your Mem0 MCP server:

```bash
pip install -e ".[smithery]"          # if you're developing locally
export MEM0_API_KEY="sk_mem0_..."
export OPENAI_API_KEY="sk-openai-..."  # or another supported provider
python example/pydantic_ai_repl.py
```

This script launches `mem0_mcp_server.server` via the bundled `example/config.json`, then connects a Pydantic AI agent (“Mem0Guide”) over stdio. Use it to sanity-check your API key with prompts like “search memories for favorite food.” The agent now inherits `MEM0_DEFAULT_USER_ID` from your environment/session config, so set that value if you don’t want the fallback `mem0-mcp`. Override the config path or server key via `MEM0_MCP_CONFIG_PATH` / `MEM0_MCP_CONFIG_SERVER` if you want to target a Smithery/Docker endpoint instead, or reuse the same config files in any other MCP client. For a full end-to-end walkthrough (stdio, Smithery HTTP, Docker HTTP) see `LOCAL_TESTING.md`.

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
- `add_memory(text?, messages?, user_id?, agent_id?, run_id?, metadata?, enable_graph?)`
- `search_memories(query, filters?, limit?, enable_graph?)`
- `get_memories(filters?, page?, page_size?, enable_graph?)`
- `get_memory(memory_id)`
- `update_memory(memory_id, text)`
- `delete_memory(memory_id)`
- `delete_all_memories(user_id?, agent_id?, app_id?, run_id?)`
- `delete_entities(user_id?, agent_id?, app_id?, run_id?)`
- `list_entities()`

All responses are JSON strings returned directly from the Mem0 API via the official `mem0ai` SDK.

## Development

```bash
uv sync --python 3.11                  # optional, installs dev extras and lockfile
uv run --from . mem0-mcp-server        # run local checkout via uvx
```

## License
MIT
