# Local Testing Cookbook

Use this after cloning the repo to validate every delivery path (stdio CLI,
Smithery HTTP, Docker HTTP) without publishing to PyPI. You will:

1. Install the package in editable mode so code changes take effect immediately.
2. Export your Mem0/OpenAI keys once.
3. Run the bundled Pydantic AI REPL against each transport by swapping MCP
   config files.

## Prerequisites

- Python 3.10+, `pip`, and preferably `uv`
- Docker (for the container scenario)
- A Mem0 API key (`MEM0_API_KEY`)
- Optional: Smithery CLI support (`pip install "mem0-mcp-server[smithery]"`)

## 1. Clone & Install

```bash
git clone https://github.com/mem0-ai/mem0-mcp-server.git
cd mem0-mcp-server
pip install -e ".[smithery]"
```

## 2. Export Environment Variables (once per shell)

```bash
export MEM0_API_KEY="sk_mem0_..."
export MEM0_DEFAULT_USER_ID="your-handle"   # optional
export OPENAI_API_KEY="sk-openai_..."      # required only for the REPL
```

Unless noted, leave `MEM0_MCP_CONFIG_PATH` unset so the REPL defaults to
`example/config.json`.

`$REPO_ROOT` refers to this directory.

---

## Scenario A – Local StdIO / CLI

Run the stdio transport just like PyPI users would.

```bash
uvx mem0-mcp-server    # or python -m mem0_mcp_server.server
```

Test via the REPL (launches `example/config.json`, which runs the server in
process):

```bash
python example/pydantic_ai_repl.py
```

Prompts like “Remember that I love tiramisu” should succeed; watch the stdio
terminal for tool logs.

---

## Scenario B – Smithery HTTP (local CLI)

Use the Smithery CLI to expose `http://127.0.0.1:8081/mcp`.

```bash
uv run smithery dev          # optional: uv run smithery playground
```

Create an HTTP config (e.g., `/tmp/smithery-config.json`):

```json
{
  "mcpServers": {
    "mem0-smithery": {
      "type": "http",
      "url": "http://127.0.0.1:8081/mcp"
    }
  }
}
```

Run the REPL against it:

```bash
export MEM0_MCP_CONFIG_PATH=/tmp/smithery-config.json
export MEM0_MCP_CONFIG_SERVER=mem0-smithery
python example/pydantic_ai_repl.py
```

The agent now talks to the HTTP endpoint instead of spawning stdio.

---

## Scenario C – Docker HTTP

Build the container and expose port 8081.

```bash
docker build -t mem0-mcp-server .
docker run --rm -e MEM0_API_KEY="sk_mem0_..." -p 8081:8081 mem0-mcp-server
```

Leave this terminal running. In a second terminal:

```bash
export MEM0_MCP_CONFIG_PATH="$PWD/example/docker-config.json"
export MEM0_MCP_CONFIG_SERVER=mem0-docker
python example/pydantic_ai_repl.py
```

You should see tool logs in the Docker terminal whenever the agent calls Mem0.

---

## Config Cheat Sheet

| Use case      | Config file / snippet                                                          | Notes                                            |
| ------------- | ------------------------------------------------------------------------------ | ------------------------------------------------ |
| StdIO (local) | `example/config.json`                                                          | Default; no env tweaks needed.                   |
| Smithery HTTP | Copy `example/config.json`, set `type="http"`, `url=http://127.0.0.1:8081/mcp` | Remember to set `MEM0_MCP_CONFIG_PATH`/`SERVER`. |
| Docker HTTP   | `example/docker-config.json`                                                   | Container must run with `-e MEM0_API_KEY`.       |

Whatever transport you choose, the server process itself must receive
`MEM0_API_KEY` (and optional `MEM0_DEFAULT_USER_ID`). Passing `-e MEM0_API_KEY=…`
to `docker run` or configuring env vars in Smithery is mandatory.
