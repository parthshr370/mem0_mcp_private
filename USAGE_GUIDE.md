# Mem0 MCP Server Guide

Connect your AI assistants to Mem0's long-term memory using the Model Context Protocol (MCP).

## What is MCP?

The **Model Context Protocol (MCP)** is a standard that allows AI models (like Claude) to connect to external tools and data sources. This server acts as a bridge, enabling your AI to read and write memories to Mem0 securely.

## Exposed Tools

Your AI gains the following capabilities:

| Tool                  | Description                                |
| :-------------------- | :----------------------------------------- |
| `add_memory`          | Save text or conversation history.         |
| `search_memories`     | Semantic search against past interactions. |
| `get_memories`        | List memories with filters and pagination. |
| `get_memory`          | Retrieve a specific memory by ID.          |
| `update_memory`       | Update a memory's content.                 |
| `delete_memory`       | Delete a specific memory.                  |
| `delete_all_memories` | Wipe all memories for a user/agent.        |
| `list_entities`       | List users/agents with stored memories.    |

## Installation

Install via pip:

```bash
pip install mem0-mcp-server
```

Need HTTP + Smithery tooling? Install the optional extras:

```bash
pip install "mem0-mcp-server[smithery]"
```

## Configuration

The server requires the following environment variables:

- `MEM0_API_KEY` (Required): Your API key from [mem0.ai](https://mem0.ai).
- `MEM0_DEFAULT_USER_ID` (Optional): Default user ID for operations (defaults to `mem0-mcp`).

## Quick Start: Pydantic AI Example

The package includes a built-in Pydantic AI agent to verify functionality. The
easiest path is the standalone script in `example/pydantic_ai_repl.py`, which
loads `example/config.json` and launches your local MCP server automatically.

1. Export your keys:

   ```bash
   export MEM0_API_KEY="sk_mem0_..."
   export OPENAI_API_KEY="sk-proj-..."
   ```

2. Run the agent:
   ```bash
   python example/pydantic_ai_repl.py
   ```

You can now chat with the agent in your terminal. It will use Mem0 to store and recall information. The agent respects `MEM0_DEFAULT_USER_ID` from your environment/session config, so set that value before running if you don’t want the fallback `mem0-mcp`.

## Deployment Options

- **Local stdio (default)**: `uvx mem0-mcp-server` reads `MEM0_API_KEY` from your environment and serves MCP over stdio. Ideal for Claude Desktop/Cursor `uvx` integrations.
- **Local HTTP / Smithery CLI**: install `[smithery]`, then `uv run smithery dev` (HTTP) or `uv run smithery playground` (ngrok tunnel) to test the HTTP transport or connect to Smithery’s playground.
- **Docker / hosted HTTP**: build the repo’s `Dockerfile` to get a container that runs `uv run smithery dev` internally. Set `MEM0_API_KEY` (and optionally `MEM0_DEFAULT_USER_ID`) at runtime; expose the container’s port (Smithery expects `PORT=8081`).

## Integration Examples

### 1. Claude Desktop App

Configure Claude to use Mem0 by editing your `claude_desktop_config.json`. We recommend using `uvx` to run the server directly.

```json
{
  "mcpServers": {
    "mem0": {
      "command": "uvx",
      "args": ["mem0-mcp-server"],
      "env": {
        "MEM0_API_KEY": "sk_mem0_..."
      }
    }
  }
}
```

### 2. Custom Python Agent

To connect a custom agent (e.g., using LangChain or vanilla Python):

```python
from mcp.client.stdio import StdioServerParameters, stdio_client

server_params = StdioServerParameters(
    command="uvx",
    args=["mem0-mcp-server"],
    env={"MEM0_API_KEY": "sk_mem0_..."}
)

async with stdio_client(server_params) as (read, write):
    # Initialize your MCP client here
    pass
```
