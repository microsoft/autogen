"""Dakera persistent memory for AutoGen agents.

Self-hosted, decay-weighted vector memory server.
Self-host: docker run -p 3300:3300 -e DAKERA_API_KEY=key ghcr.io/dakera-ai/dakera:latest
Install: pip install autogen-ext[dakera]
"""

import logging
import os
from typing import Any, List, Optional

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.memory import Memory, MemoryContent, MemoryMimeType, MemoryQueryResult, UpdateContextResult
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from pydantic import BaseModel, Field, SecretStr

logger = logging.getLogger(__name__)


class DakeraMemoryConfig(BaseModel):
    """Configuration for the DakeraMemory component."""

    base_url: str = Field(
        default="http://localhost:3300",
        description="Base URL of the self-hosted Dakera server.",
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="Dakera API key. Falls back to DAKERA_API_KEY env var.",
    )
    agent_id: str = Field(
        default="autogen",
        description="Namespace for memory isolation. Use different values per agent.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session grouping. Memories are shared across all sessions if None.",
    )
    top_k: int = Field(
        default=5,
        description="Number of memories to retrieve per query.",
    )
    timeout: float = Field(
        default=10.0,
        description="HTTP request timeout in seconds.",
    )


class DakeraMemory(Memory, Component[DakeraMemoryConfig]):
    """Persistent, decay-weighted memory for AutoGen agents backed by self-hosted Dakera.

    Unlike Mem0 (cloud-only) or ChromaDB (local-only), Dakera provides network-accessible
    persistent memory that runs entirely on your infrastructure. Multiple agents can share
    the same Dakera server with namespace isolation via ``agent_id``.

    Dakera uses access-weighted importance scoring: memories that are recent and
    frequently accessed rank higher than stale, rarely-accessed ones.

    Args:
        config: DakeraMemoryConfig with server URL, API key, and recall settings.

    Example:
        .. code-block:: python

            from autogen_agentchat.agents import AssistantAgent
            from autogen_ext.memory.dakera import DakeraMemory, DakeraMemoryConfig
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            memory = DakeraMemory(
                DakeraMemoryConfig(
                    base_url=\"http://localhost:3300\",
                    api_key=\"dk_your_key\",
                    agent_id=\"support-agent\",
                    top_k=5,
                )
            )

            agent = AssistantAgent(
                \"support\",
                model_client=OpenAIChatCompletionClient(model=\"gpt-4o\"),
                memory=[memory],
            )
    """

    component_config_schema = DakeraMemoryConfig
    component_provider_override = "autogen_ext.memory.dakera.DakeraMemory"

    def __init__(self, config: Optional[DakeraMemoryConfig] = None) -> None:
        self._config = config or DakeraMemoryConfig()

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        key: Optional[str] = None
        if self._config.api_key:
            key = self._config.api_key.get_secret_value()
        if not key:
            key = os.getenv("DAKERA_API_KEY")
        if key:
            h["Authorization"] = f"Bearer {key}"
        return h

    def _base_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"agent_id": self._config.agent_id}
        if self._config.session_id:
            payload["session_id"] = self._config.session_id
        return payload

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """Recall relevant memories and inject them as a SystemMessage before the model call.

        Called automatically by AutoGen before each LLM invocation when this memory
        is attached to an agent.
        """
        # Extract the latest user message as the recall query
        messages = await model_context.get_messages()
        query = ""
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if content and isinstance(content, str) and getattr(msg, "source", "") not in ("", "system"):
                query = content
                break

        if not query:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        recalled = await self._search(query)
        if not recalled:
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))

        memory_lines = "\n".join(f"- {r['content']}" for r in recalled)
        system_msg = SystemMessage(
            content=(
                f"Relevant memories from prior sessions (retrieved from Dakera):\n{memory_lines}"
            )
        )
        await model_context.add_message(system_msg)

        memory_contents = [
            MemoryContent(content=r["content"], mime_type=MemoryMimeType.TEXT, metadata=r.get("metadata"))
            for r in recalled
        ]
        return UpdateContextResult(memories=MemoryQueryResult(results=memory_contents))

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: Optional[CancellationToken] = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """Search Dakera for memories relevant to the query."""
        query_str = query if isinstance(query, str) else str(query.content)
        results = await self._search(query_str)
        return MemoryQueryResult(
            results=[
                MemoryContent(
                    content=r["content"],
                    mime_type=MemoryMimeType.TEXT,
                    metadata=r.get("metadata"),
                )
                for r in results
            ]
        )

    async def add(
        self,
        content: MemoryContent,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        """Store a memory entry in Dakera."""
        text = content.content if isinstance(content.content, str) else str(content.content)
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                await client.post(
                    f"{self._config.base_url}/v1/memories",
                    headers=self._headers(),
                    json={**self._base_payload(), "content": text},
                )
        except httpx.HTTPError as exc:
            logger.warning("DakeraMemory.add failed: %s", exc)

    async def clear(self) -> None:
        """Delete all memories for the configured agent_id/session_id."""
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                await client.delete(
                    f"{self._config.base_url}/v1/memories",
                    headers=self._headers(),
                    json=self._base_payload(),
                )
        except httpx.HTTPError as exc:
            logger.warning("DakeraMemory.clear failed: %s", exc)

    async def close(self) -> None:
        """No persistent connection to close."""

    async def _search(self, query: str) -> List[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                resp = await client.post(
                    f"{self._config.base_url}/v1/memories/search",
                    headers=self._headers(),
                    json={**self._base_payload(), "query": query, "top_k": self._config.top_k},
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
        except httpx.HTTPError as exc:
            logger.warning("DakeraMemory._search failed: %s", exc)
            return []
