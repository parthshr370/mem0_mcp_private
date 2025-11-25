"""MCP server that exposes Mem0 REST endpoints as MCP tools."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mem0.exceptions import MemoryError

from mem0 import MemoryClient

try:  # Support both package (`python -m mem0_mcp.server`) and script (`python mem0_mcp/server.py`) runs.
    from .schemas import (
        AddMemoryArgs,
        DeleteAllArgs,
        DeleteEntitiesArgs,
        GetMemoriesArgs,
        SearchMemoriesArgs,
        ToolMessage,
    )
except ImportError:  # pragma: no cover - fallback for script execution
    from schemas import (
        AddMemoryArgs,
        DeleteAllArgs,
        DeleteEntitiesArgs,
        GetMemoriesArgs,
        SearchMemoriesArgs,
        ToolMessage,
    )

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("mem0_mcp_server")

MEM0_API_KEY = os.getenv("MEM0_API_KEY")
DEFAULT_USER_ID = os.getenv("MEM0_DEFAULT_USER_ID", "parthshr370")

if not MEM0_API_KEY:
    raise RuntimeError("MEM0_API_KEY is required to start the Mem0 MCP server.")

mem0_client = MemoryClient(api_key=MEM0_API_KEY)
mcp = FastMCP("mem0")


def _with_default_filters(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ensure filters exist and include the default user_id at the top level."""
    if not filters:
        # most basic fallback filter for all queries
        return {"AND": [{"user_id": DEFAULT_USER_ID}]}
    if not any(key in filters for key in ("AND", "OR", "NOT")):
        filters = {"AND": [filters]}
    has_user = json.dumps(filters, sort_keys=True).find('"user_id"') != -1
    if not has_user:
        and_list = filters.setdefault("AND", [])
        if not isinstance(and_list, list):
            raise ValueError("filters['AND'] must be a list when present.")
        and_list.insert(0, {"user_id": DEFAULT_USER_ID})
    return filters


def _mem0_call(func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
    except MemoryError as exc:  # surface structured error back to MCP client
        logger.error("Mem0 call failed: %s", exc)
        # returns the erorr to the model
        return json.dumps(
            {
                "error": str(exc),
                "status": getattr(exc, "status", None),
                "payload": getattr(exc, "payload", None),
            },
            ensure_ascii=False,
        )
    return json.dumps(result, ensure_ascii=False)


# graph is disabled by default to make queries simpler and fast
# Mention " Enable/Use graph while calling memory " in your system prompt to run it in each instance


@mcp.tool()
def add_memory(
    text: Optional[str] = None,
    messages: Optional[list[Dict[str, str]]] = None,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    enable_graph: Optional[bool] = None,
) -> str:
    """Write durable information to Mem0.

    Default path for new or casually-updated facts—Mem0 deduplicates/merges automatically. Provide
    either a simple `text` string (converted to a user message automatically) or an explicit list of
    role/content messages for richer context. For cases where the user explicitly points to an
    existing memory that must be edited, prefer search_memories + update_memory instead of this helper.The call falls back to the default user_id when not provided. Leave enable_graph alone unless the user explicitly opts into graph linking.
    """
    args = AddMemoryArgs(
        text=text,
        messages=[ToolMessage(**msg) for msg in messages] if messages else None,
        user_id=user_id or DEFAULT_USER_ID,
        agent_id=agent_id,
        run_id=run_id,
        metadata=metadata,
        enable_graph=enable_graph,
    )
    payload = args.model_dump(exclude_none=True)
    payload.setdefault("enable_graph", False)
    conversation = payload.pop("messages", None)
    if not conversation:
        derived_text = payload.pop("text", None)
        if derived_text:
            conversation = [{"role": "user", "content": derived_text}]
        else:
            return json.dumps(
                {
                    "error": "messages_missing",
                    "detail": "Provide either `text` or `messages` so Mem0 knows what to store.",
                },
                ensure_ascii=False,
            )
    else:
        # model_dump returns dicts already, so drop the optional text field
        payload.pop("text", None)

    return _mem0_call(mem0_client.add, conversation, **payload)


@mcp.tool()
def search_memories(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    enable_graph: Optional[bool] = None,
) -> str:
    """Semantic search against existing memories.

    Choose this for “find X” prompts or to gather candidate IDs before delete/update flows. Filters
    are automatically AND-wrapped with the default user_id, so you rarely need to specify it. Only
    send enable_graph=True when the user wants graph-enhanced recall.
    """
    args = SearchMemoriesArgs(
        query=query,
        filters=filters,
        limit=limit,
        enable_graph=enable_graph,
    )
    payload = args.model_dump(exclude_none=True)
    payload["filters"] = _with_default_filters(payload.get("filters"))
    payload.setdefault(
        "enable_graph", False
    )  # remains false unless mentioned in prompt
    return _mem0_call(mem0_client.search, **payload)


@mcp.tool()
def get_memories(
    filters: Optional[Dict[str, Any]] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    enable_graph: Optional[bool] = None,
) -> str:
    """List memories via structured filters or pagination.

    Use for “show/get all memories” so you can echo every memory_id back to the user. Filters are
    scoped to the default user_id automatically, and you can page through large sets with page/page_size.
    Keep enable_graph False unless users explicitly ask for graph memories.
    """
    args = GetMemoriesArgs(
        filters=filters,
        page=page,
        page_size=page_size,
        enable_graph=enable_graph,
    )
    payload = args.model_dump(exclude_none=True)
    payload["filters"] = _with_default_filters(payload.get("filters"))
    payload.setdefault("enable_graph", False)
    return _mem0_call(mem0_client.get_all, **payload)


@mcp.tool()
def delete_all_memories(
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    app_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Bulk-delete every memory in the confirmed scope.

    Only invoke after the user explicitly confirms the user/agent/app/run to wipe. Defaults to the
    server's user_id when not provided so "forget everything" flows succeed without extra loops.
    """
    args = DeleteAllArgs(
        user_id=user_id or DEFAULT_USER_ID,
        agent_id=agent_id,
        app_id=app_id,
        run_id=run_id,
    )
    payload = args.model_dump(exclude_none=True)
    return _mem0_call(mem0_client.delete_all, **payload)


@mcp.tool()
def list_entities() -> str:
    """List users/agents/apps/runs with stored memories so the user can pick a scope."""
    return _mem0_call(mem0_client.users)


@mcp.tool()
def get_memory(memory_id: str) -> str:
    """Retrieve a single memory once the user has picked an exact ID."""
    return _mem0_call(mem0_client.get, memory_id)


@mcp.tool()
def update_memory(memory_id: str, text: str) -> str:
    """Overwrite an existing memory’s text after the user confirms the exact memory_id."""
    return _mem0_call(mem0_client.update, memory_id=memory_id, text=text)


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """Delete a memory once the user explicitly confirms the memory_id to remove."""
    return _mem0_call(mem0_client.delete, memory_id)


@mcp.tool()
def delete_entities(
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    app_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Delete a user/agent/app/run (and its memories) once the user confirms the scope.

    Ideal for "wipe this agent/app" requests. At least one identifier must be supplied; if the user
    is unsure, ask them to run list_entities first and then confirm.
    """
    args = DeleteEntitiesArgs(
        user_id=user_id,
        agent_id=agent_id,
        app_id=app_id,
        run_id=run_id,
    )
    if not any([args.user_id, args.agent_id, args.app_id, args.run_id]):
        return json.dumps(
            {
                "error": "scope_missing",
                "detail": "Provide user_id, agent_id, app_id, or run_id before calling delete_entities.",
            },
            ensure_ascii=False,
        )
    payload = args.model_dump(exclude_none=True)
    return _mem0_call(mem0_client.delete_users, **payload)


def main() -> None:
    """Run the MCP server over stdio."""
    logger.info("Starting Mem0 MCP server (default user=%s)", DEFAULT_USER_ID)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
