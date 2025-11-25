# Mem0 MCP Server

[![PyPI version](https://img.shields.io/pypi/v/mem0-mcp-server.svg)](https://pypi.org/project/mem0-mcp-server/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`mem0-mcp-server` wraps the official [Mem0](https://mem0.ai) Memory API as a Model Context Protocol (MCP) server so any MCP-compatible client (Claude Desktop, Cursor, custom agents) can add, search, update, and delete long-term memories. The package bundles a stdio transport entry point so you can run it instantly with `uvx mem0-mcp-server` or by installing via `pip`.

## Quick Start

```bash
pip install mem0-mcp-server
export MEM0_API_KEY="sk_mem0_..."
export MEM0_DEFAULT_USER_ID="your-handle"   # optional
mem0-mcp-server
```

Or no install needed:

```bash
uvx mem0-mcp-server
```

You should immediately see `Starting Mem0 MCP server (default user=...)`, after which the server waits on stdio for whatever MCP host you connect.

### Environment Variables
- `MEM0_API_KEY` (required) – Mem0 platform API key.
- `MEM0_DEFAULT_USER_ID` (optional) – default `user_id` injected into filters and write requests (defaults to `parthshr370`).
- `MEM0_MCP_AGENT_MODEL` (optional, example helper only) – default LLM for the bundled Pydantic AI example.

### Running the Pydantic AI example (optional)

```bash
export OPENAI_API_KEY="sk-openai-..."      # or another Pydantic AI-supported provider
python -m mem0_mcp_server.example_mcp_run
```

This script (`example_mcp_run.py`) is built with [Pydantic AI](https://github.com/pydantic/pydantic-ai); it launches a REPL agent that automatically calls the Mem0 MCP tools on your behalf. Use it to sanity-check your API key: ask for “memories about favorite food” and it will go through `search_memories` end to end. The agent loads `config.json` (shipped with the package) using `pydantic_ai.mcp.load_mcp_servers`, so the exact same config block that works for Claude/Cursor is honored locally too. Override the file location via `MEM0_MCP_CONFIG_PATH` or select another server key via `MEM0_MCP_CONFIG_SERVER`.

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

The package includes `src/mem0_mcp_server/config.json`, a ready-to-use template that matches the snippet above and supports `${VAR}` expansion (handled by `load_mcp_servers`). Point Claude Desktop (or any host) at the file verbatim, or copy/paste it into your own config store. The `example_mcp_run` helper reads this file as well, so every client—GUI or CLI—can share a single authoritative configuration.

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
