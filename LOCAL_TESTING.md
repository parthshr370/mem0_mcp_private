# Local Testing Cookbook

This guide mirrors everything we walked through manually: build/run the Mem0 MCP
server three ways (stdio CLI, Smithery HTTP, Docker HTTP) and point the bundled
Pydantic AI agent at each mode. All commands assume you’re at the repo root
(`$REPO_ROOT`, e.g., `~/Downloads/mem0_mcp_private`) and have already run
`pip install -e ".[smithery]"` within your Python environment.

## 0. Common Setup

```bash
cd $REPO_ROOT
export MEM0_API_KEY="sk_mem0_..."
export MEM0_DEFAULT_USER_ID="your-handle"   # optional
export OPENAI_API_KEY="sk-openai_..."      # needed for the Pydantic REPL
```

When using the REPL, leave `MEM0_MCP_CONFIG_PATH` unset unless a scenario below
explicitly tells you to set it.

## 1. Local StdIO / Package CLI

### Run the MCP server

```bash
uvx mem0-mcp-server     # or python -m mem0_mcp_server.server
```

This starts FastMCP over stdio on your terminal. Point Claude/Cursor at the
`uvx mem0-mcp-server` command or keep it open for manual tests.

### Test with the Pydantic REPL

```bash
python example/pydantic_ai_repl.py
```

Because `MEM0_MCP_CONFIG_PATH` is unset, the REPL loads `example/config.json`,
which launches `python -m mem0_mcp_server.server` in-process. Prompts like
“Remember that I love tiramisu” should succeed, and you’ll see tool logs in the
same terminal.

## 2. Smithery HTTP (local CLI)

### Start the HTTP server

```bash
uv run smithery dev        # hosts http://127.0.0.1:8081/mcp
```

Optional: `uv run smithery playground` opens an ngrok tunnel + web playground.

### Point the Pydantic REPL at Smithery

Create (or reuse) a config file that references the HTTP endpoint; easiest is
to copy `example/config.json`, replace `command/args` with an HTTP entry, and
save it somewhere (e.g., `/tmp/smithery-config.json`):

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

Then run:

```bash
export MEM0_MCP_CONFIG_PATH=/tmp/smithery-config.json
export MEM0_MCP_CONFIG_SERVER=mem0-smithery
python example/pydantic_ai_repl.py
```

The REPL now talks to the Smithery HTTP server instead of spawning stdio.

## 3. Docker HTTP

### Build & run the container

```bash
docker build -t mem0-mcp-server .
docker run --rm -e MEM0_API_KEY="sk_mem0_..." -p 8081:8081 mem0-mcp-server
```

Leave the container running; it serves `http://localhost:8081/mcp`.

### Point the Pydantic REPL at Docker

Use the bundled HTTP config:

```bash
export MEM0_MCP_CONFIG_PATH="$PWD/example/docker-config.json"
export MEM0_MCP_CONFIG_SERVER=mem0-docker
python example/pydantic_ai_repl.py
```

You should see tool logs inside the Docker container’s terminal whenever the
agent calls Mem0.

## Switching Configs Quickly

| Scenario        | Config file                     | Environment tweaks                               |
|-----------------|---------------------------------|--------------------------------------------------|
| Local stdio     | `example/config.json` (default) | Leave `MEM0_MCP_CONFIG_PATH` unset               |
| Smithery HTTP   | Custom HTTP JSON (see above)    | Set `MEM0_MCP_CONFIG_PATH` + `MEM0_MCP_CONFIG_SERVER` |
| Docker HTTP     | `example/docker-config.json`    | Same as Smithery but point to provided file      |

Remember the container/server still needs `MEM0_API_KEY` in *its* environment.
Passing `-e MEM0_API_KEY=...` to `docker run` or configuring Smithery’s hosted
env block is mandatory.
