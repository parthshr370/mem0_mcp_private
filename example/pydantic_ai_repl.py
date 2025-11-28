"""Standalone Pydantic AI REPL wired to the Mem0 MCP server.

Run this script from the repo root after installing the package (e.g.,
`pip install -e .[smithery]`). It defaults to the bundled `example/config.json`
so you can connect to the local `mem0_mcp_server.server` entry point without
touching `uvx`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, load_mcp_servers

EXAMPLE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXAMPLE_DIR.parent

# Ensure `src/` is importable when running directly from the repo without
# installing the editable package first. Safe no-op if already installed.
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"
_env_config_raw = os.getenv("MEM0_MCP_CONFIG_PATH")
if not _env_config_raw:
    CONFIG_PATH = DEFAULT_CONFIG_PATH
else:
    CONFIG_PATH = Path(_env_config_raw).expanduser()
CONFIG_SERVER_KEY = os.getenv("MEM0_MCP_CONFIG_SERVER", "mem0-local")
DEFAULT_MODEL = os.getenv("MEM0_MCP_AGENT_MODEL", "openai:gpt-5")
DEFAULT_TIMEOUT = int(os.getenv("MEM0_MCP_SERVER_TIMEOUT", "30"))


def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"{var_name} must be set before running the agent.")
    return value


def _select_server_index() -> int:
    """Return the index of the requested server key inside the config file."""

    try:
        config = json.loads(CONFIG_PATH.read_text())
    except FileNotFoundError:
        return -1
    servers = config.get("mcpServers") or {}
    if not servers:
        raise RuntimeError(f"No 'mcpServers' definitions found in {CONFIG_PATH}")
    keys = list(servers.keys())
    if CONFIG_SERVER_KEY not in servers:
        if CONFIG_SERVER_KEY:
            raise RuntimeError(
                f"Server '{CONFIG_SERVER_KEY}' not found in {CONFIG_PATH}. Available: {keys}"
            )
        return 0
    return keys.index(CONFIG_SERVER_KEY)


def _load_server_from_config() -> MCPServerStdio | None:
    """Load the MCP server definition from config.json if present."""

    if not CONFIG_PATH.exists():
        return None
    index = _select_server_index()
    servers = load_mcp_servers(CONFIG_PATH)
    if not servers:
        raise RuntimeError(f"{CONFIG_PATH} did not produce any MCP servers.")
    if index >= len(servers):
        raise RuntimeError(
            f"Server index {index} is out of range for {CONFIG_PATH}; found {len(servers)} servers."
        )
    return servers[index]


def build_server() -> MCPServerStdio:
    """Launch the Mem0 MCP server over stdio with inherited env vars."""

    env = os.environ.copy()
    _require_env("MEM0_API_KEY")  # fail fast with a helpful error

    configured = _load_server_from_config()
    if configured:
        return configured

    server_path = PROJECT_ROOT / "src" / "mem0_mcp_server" / "server.py"
    return MCPServerStdio(
        sys.executable,
        args=[str(server_path)],
        env=env,
        timeout=DEFAULT_TIMEOUT,
    )


def build_agent(server: MCPServerStdio) -> tuple[Agent, str]:
    """Create a Pydantic AI agent that can use the Mem0 MCP tools."""

    system_prompt = (
        "You are Mem0Guide, a friendly assistant whose ONLY external actions are the Mem0 MCP tools. "
        "Default to the configured MEM0_DEFAULT_USER_ID (env or session config) unless the user supplies another value, and inject it into every filter. "
        "Operating loop: (1) treat any new preference, fact, or personal detail as durable—call add_memory immediately (even if the user doesn’t say 'remember') unless they explicitly opt out; when a new detail supersedes an earlier one, summarize both points (e.g., 'was planning Berlin, now relocating to San Francisco') so the latest truth is clear, (2) only run the search → list IDs → confirm → update/delete flow when the user references an existing memory or when multiple matches would be risky, (3) get/show/list requests should use one combined get_memories or search_memories call (expand synonyms yourself), (4) for destructive bulk actions like delete_all_memories or delete_entities ask for scope once—if the user immediately confirms (yes, delete all my memories), execute without re-asking, (5) keep graph opt-in only. "
        "Act decisively: remember the most recent confirmation context so you can honor a follow-up 'yes/confirm' without repeating questions, run the tool that best matches the request, mention what you ran, summarize the outcome naturally, and offer one concise next step. Mention memory_ids only when the action depends on them. Ask clarifying questions only when you truly lack enough info to proceed or the user’s safety could be compromised."
    )
    model = os.getenv("MEM0_MCP_AGENT_MODEL", DEFAULT_MODEL)
    agent = Agent(model=model, toolsets=[server], system_prompt=system_prompt)
    return agent, model


def _print_banner(model: str) -> None:
    print("Mem0 Pydantic AI agent ready. Type a prompt or 'exit' to quit.\n")
    print(f"Model: {model}")
    print("Tools: Mem0 MCP (add/search/get/update/delete)\n")


async def chat_loop(agent: Agent, server: MCPServerStdio, model_name: str) -> None:
    """Interactive REPL that streams requests through the agent."""

    async with server:
        async with agent:
            _print_banner(model_name)
            while True:
                try:
                    user_input = input("You> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye!")
                    return
                if not user_input:
                    continue
                if user_input.lower() in {"exit", "quit"}:
                    print("Bye!")
                    return
                result = await agent.run(user_input)
                print(f"\nAgent> {result.output}\n")


async def main() -> None:
    load_dotenv()
    server = build_server()
    agent, model_name = build_agent(server)
    await chat_loop(agent, server, model_name)


if __name__ == "__main__":
    asyncio.run(main())
