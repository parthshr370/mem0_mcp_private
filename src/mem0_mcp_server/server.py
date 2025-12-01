"""MCP server that exposes Mem0 REST endpoints as MCP tools."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from mem0 import MemoryClient
from mem0.exceptions import MemoryError

try:  # Support both package (`python -m mem0_mcp.server`) and script (`python mem0_mcp/server.py`) runs.
    from .schemas import (
        AddMemoryArgs,
        ConfigSchema,
        DeleteAllArgs,
        DeleteEntitiesArgs,
        GetMemoriesArgs,
        SearchMemoriesArgs,
        ToolMessage,
    )
except ImportError:  # pragma: no cover - fallback for script execution
    from schemas import (
        AddMemoryArgs,
        ConfigSchema,
        DeleteAllArgs,
        DeleteEntitiesArgs,
        GetMemoriesArgs,
        SearchMemoriesArgs,
        ToolMessage,
    )

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("mem0_mcp_server")




try:
    from smithery.decorators import smithery as smithery_module
except ImportError:  # pragma: no cover - Smithery optional

    def smithery_server(*args, **kwargs):  # type: ignore[override]
        def decorator(func):
            return func

        return decorator


else:

    def smithery_server(*args, **kwargs):  # pragma: no cover - exercised in Smithery env
        return smithery_module.server(*args, **kwargs)


# graph remains off by default , also set the default user_id to "mem0-mcp" when nothing set
ENV_API_KEY = os.getenv("MEM0_API_KEY")
ENV_DEFAULT_USER_ID = os.getenv("MEM0_DEFAULT_USER_ID", "mem0-mcp")
ENV_ENABLE_GRAPH_DEFAULT = os.getenv("MEM0_ENABLE_GRAPH_DEFAULT", "false").lower() in {
    "1",
    "true",
    "yes",
}

_CLIENT_CACHE: Dict[str, MemoryClient] = {}


def _config_value(source: Any, field: str):
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(field)
    return getattr(source, field, None)


def _with_default_filters(
    default_user_id: str, filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Ensure filters exist and include the default user_id at the top level."""
    if not filters:
        return {"AND": [{"user_id": default_user_id}]}
    if not any(key in filters for key in ("AND", "OR", "NOT")):
        filters = {"AND": [filters]}
    has_user = json.dumps(filters, sort_keys=True).find('"user_id"') != -1
    if not has_user:
        and_list = filters.setdefault("AND", [])
        if not isinstance(and_list, list):
            raise ValueError("filters['AND'] must be a list when present.")
        and_list.insert(0, {"user_id": default_user_id})
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


def _resolve_settings(
    ctx: Context | None,
    base_config: ConfigSchema | None,
) -> tuple[str, str, bool]:
    session_config = getattr(ctx, "session_config", None)
    api_key = (
        _config_value(session_config, "mem0_api_key")
        or (base_config.mem0_api_key if base_config else None)
        or ENV_API_KEY
    )
    if not api_key:
        raise RuntimeError(
            "MEM0_API_KEY is required (via session config or environment) to run the Mem0 MCP server."
        )

    default_user = (
        _config_value(session_config, "default_user_id")
        or (base_config.default_user_id if base_config else None)
        or ENV_DEFAULT_USER_ID
    )
    enable_graph_default = _config_value(session_config, "enable_graph_default")
    if enable_graph_default is None:
        enable_graph_default = base_config.enable_graph_default if base_config else None
    if enable_graph_default is None:
        enable_graph_default = ENV_ENABLE_GRAPH_DEFAULT

    return api_key, default_user, enable_graph_default


# init the client
def _mem0_client(api_key: str) -> MemoryClient:
    client = _CLIENT_CACHE.get(api_key)
    if client is None:
        client = MemoryClient(api_key=api_key)
        _CLIENT_CACHE[api_key] = client
    return client


def _default_enable_graph(enable_graph: Optional[bool], default: bool) -> bool:
    if enable_graph is None:
        return default
    return enable_graph


@smithery_server(config_schema=ConfigSchema)
def create_server(config: ConfigSchema | None = None) -> FastMCP:
    """Create a FastMCP server usable via stdio, Docker, or Smithery."""

    # Ensure env-only runs fail fast when no API key is available anywhere.
    if not (ENV_API_KEY or (config and config.mem0_api_key)):
        raise RuntimeError(
            "MEM0_API_KEY is required via environment variables or Smithery session config."
        )

    server = FastMCP("mem0")

    # graph is disabled by default to make queries simpler and fast
    # Mention " Enable/Use graph while calling memory " in your system prompt to run it in each instance

    @server.tool(description="Store a user’s new preference, fact, or conversation snippet.")
    def add_memory(
        text: Optional[str] = None,
        messages: Optional[list[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        enable_graph: Optional[bool] = None,
        ctx: Context | None = None,
    ) -> str:
        """Write durable information to Mem0."""

        api_key, default_user, graph_default = _resolve_settings(ctx, config)
        args = AddMemoryArgs(
            text=text,
            messages=[ToolMessage(**msg) for msg in messages] if messages else None,
            user_id=user_id or default_user,
            agent_id=agent_id,
            app_id=app_id,
            run_id=run_id,
            metadata=metadata,
            enable_graph=_default_enable_graph(enable_graph, graph_default),
        )
        payload = args.model_dump(exclude_none=True)
        payload.setdefault("enable_graph", graph_default)
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
            payload.pop("text", None)

        client = _mem0_client(api_key)
        return _mem0_call(client.add, conversation, **payload)

    @server.tool(description="Run a semantic search over existing memories.")
    def search_memories(
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        enable_graph: Optional[bool] = None,
        ctx: Context | None = None,
    ) -> str:
        """Semantic search against existing memories."""

        api_key, default_user, graph_default = _resolve_settings(ctx, config)
        args = SearchMemoriesArgs(
            query=query,
            filters=filters,
            limit=limit,
            enable_graph=_default_enable_graph(enable_graph, graph_default),
        )
        payload = args.model_dump(exclude_none=True)
        payload["filters"] = _with_default_filters(default_user, payload.get("filters"))
        payload.setdefault("enable_graph", graph_default)
        client = _mem0_client(api_key)
        return _mem0_call(client.search, **payload)

    @server.tool(description="Page through memories using filters instead of search.")
    def get_memories(
        filters: Optional[Dict[str, Any]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        enable_graph: Optional[bool] = None,
        ctx: Context | None = None,
    ) -> str:
        """List memories via structured filters or pagination."""

        api_key, default_user, graph_default = _resolve_settings(ctx, config)
        args = GetMemoriesArgs(
            filters=filters,
            page=page,
            page_size=page_size,
            enable_graph=_default_enable_graph(enable_graph, graph_default),
        )
        payload = args.model_dump(exclude_none=True)
        payload["filters"] = _with_default_filters(default_user, payload.get("filters"))
        payload.setdefault("enable_graph", graph_default)
        client = _mem0_client(api_key)
        return _mem0_call(client.get_all, **payload)

    @server.tool(
        description="Delete every memory in the given user/agent/app/run but keep the entity."
    )
    def delete_all_memories(
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        run_id: Optional[str] = None,
        ctx: Context | None = None,
    ) -> str:
        """Bulk-delete every memory in the confirmed scope."""

        api_key, default_user, _ = _resolve_settings(ctx, config)
        args = DeleteAllArgs(
            user_id=user_id or default_user,
            agent_id=agent_id,
            app_id=app_id,
            run_id=run_id,
        )
        payload = args.model_dump(exclude_none=True)
        client = _mem0_client(api_key)
        return _mem0_call(client.delete_all, **payload)

    @server.tool(description="List which users/agents/apps/runs currently hold memories.")
    def list_entities(ctx: Context | None = None) -> str:
        """List users/agents/apps/runs with stored memories."""

        api_key, _, _ = _resolve_settings(ctx, config)
        client = _mem0_client(api_key)
        return _mem0_call(client.users)

    @server.tool(description="Fetch a single memory once you know its memory_id.")
    def get_memory(memory_id: str, ctx: Context | None = None) -> str:
        """Retrieve a single memory once the user has picked an exact ID."""

        api_key, _, _ = _resolve_settings(ctx, config)
        client = _mem0_client(api_key)
        return _mem0_call(client.get, memory_id)

    @server.tool(description="Overwrite an existing memory’s text.")
    def update_memory(memory_id: str, text: str, ctx: Context | None = None) -> str:
        """Overwrite an existing memory’s text after the user confirms the exact memory_id."""

        api_key, _, _ = _resolve_settings(ctx, config)
        client = _mem0_client(api_key)
        return _mem0_call(client.update, memory_id=memory_id, text=text)

    @server.tool(description="Delete one memory after the user confirms its memory_id.")
    def delete_memory(memory_id: str, ctx: Context | None = None) -> str:
        """Delete a memory once the user explicitly confirms the memory_id to remove."""

        api_key, _, _ = _resolve_settings(ctx, config)
        client = _mem0_client(api_key)
        return _mem0_call(client.delete, memory_id)

    @server.tool(
        description="Remove a user/agent/app/run record entirely (and cascade-delete its memories)."
    )
    def delete_entities(
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        run_id: Optional[str] = None,
        ctx: Context | None = None,
    ) -> str:
        """Delete a user/agent/app/run (and its memories) once the user confirms the scope."""

        api_key, _, _ = _resolve_settings(ctx, config)
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
        client = _mem0_client(api_key)
        return _mem0_call(client.delete_users, **payload)

    return server


def main() -> None:
    """Run the MCP server over stdio."""

    server = create_server()
    logger.info("Starting Mem0 MCP server (default user=%s)", ENV_DEFAULT_USER_ID)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
