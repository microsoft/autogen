"""
agentcard_adapters.autogen_adapter
====================================

Bidirectional adapter between Microsoft AutoGen agents and AgentCard v1.0.

Supports both AutoGen v0.2 (pyautogen) and AutoGen v0.4+ (autogen-agentchat).

Usage
-----
**Export an AutoGen AssistantAgent as AgentCard:**

    from autogen import AssistantAgent
    from agentcard_adapters.autogen_adapter import agent_to_agentcard

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful AI assistant.",
        llm_config={"model": "gpt-4o", "api_key": "..."},
    )

    card = agent_to_agentcard(
        agent=assistant,
        agent_id="01HZQK3P8EMXR9V7T5N2W4J6C0",
        endpoint_url="https://my-autogen.example.com/api/assistant",
    )
    card.validate()
    print(card.to_json(indent=2))

**Export a GroupChat as multiple AgentCards:**

    from autogen import GroupChat, GroupChatManager
    from agentcard_adapters.autogen_adapter import groupchat_to_agentcards

    groupchat = GroupChat(agents=[assistant, user_proxy], messages=[], max_round=10)
    manager = GroupChatManager(groupchat=groupchat, llm_config={...})

    cards = groupchat_to_agentcards(
        groupchat, base_url="https://my-autogen.example.com/api"
    )

**Use an AgentCard to call a remote agent from within AutoGen:**

    from agentcard_adapters.autogen_adapter import agentcard_to_tool_function

    fn, fn_schema = agentcard_to_tool_function(card)
    # Register in AssistantAgent's function_map
    assistant.register_for_llm(name=fn_schema["name"],
                                description=fn_schema["description"])(fn)

License
-------
Apache 2.0.  See https://github.com/kwailapt/AgentCard/blob/main/LICENSE
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Optional

from .core import (
    AgentCard,
    Capability,
    Endpoint,
    PricingModel,
    LANDAUER_FLOOR_JOULES,
)

if TYPE_CHECKING:
    # pyautogen / autogen-agentchat — both expose ConversableAgent
    try:
        from autogen import ConversableAgent, GroupChat
    except ImportError:
        pass

__all__ = [
    "agent_to_agentcard",
    "groupchat_to_agentcards",
    "agentcard_to_tool_function",
    "AgentCardRegistry",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _name_to_cap_id(name: str) -> str:
    """
    Convert an AutoGen agent name to a valid AgentCard capability id.

    Examples:
        "assistant"          → "assistant"
        "user_proxy"         → "user_proxy"
        "Code Executor Pro"  → "code_executor_pro"
        "GPT-4 Reasoner"     → "gpt-4_reasoner"
    """
    s = name.lower().strip()
    s = re.sub(r"[\s]+", "_", s)
    s = re.sub(r"[^a-z0-9._-]", "", s)
    s = re.sub(r"^[^a-z0-9]+", "", s)
    return s or "agent"


def _extract_functions(agent: Any) -> list[dict[str, Any]]:
    """
    Extract registered function schemas from an AutoGen agent.

    Supports both v0.2 (``function_map``) and v0.4
    (``_function_map`` / ``_tools``).
    """
    schemas: list[dict[str, Any]] = []

    # v0.2 style
    fn_map: dict[str, Any] = getattr(agent, "function_map", {}) or {}
    for fn_name in fn_map:
        schemas.append({"name": fn_name, "description": f"Function: {fn_name}"})

    # v0.4 style — _tools list of dicts with "function" key
    tools: list[Any] = getattr(agent, "_tools", []) or []
    for tool in tools:
        if isinstance(tool, dict):
            fn_info = tool.get("function", {})
            schemas.append({
                "name": fn_info.get("name", "tool"),
                "description": fn_info.get("description", ""),
                "parameters": fn_info.get("parameters"),
            })

    return schemas


# ── Single agent → AgentCard ──────────────────────────────────────────────────

def agent_to_agentcard(
    agent: "ConversableAgent",
    agent_id: str,
    endpoint_url: str,
    *,
    version: str = "1.0.0",
    protocol: str = "http",
    health_url: Optional[str] = None,
    estimated_latency_ms: Optional[float] = None,
    include_function_capabilities: bool = True,
) -> AgentCard:
    """
    Convert an AutoGen ``ConversableAgent`` to an ``AgentCard``.

    The agent's ``name`` and ``description`` (or ``system_message``) are used
    for the primary capability.  Each registered function becomes a separate
    capability under the ``fn.`` namespace.

    Parameters
    ----------
    agent:
        Any AutoGen ``ConversableAgent``, ``AssistantAgent``, or
        ``UserProxyAgent`` instance.
    agent_id:
        26-character Crockford Base32 ULID.
    endpoint_url:
        URL where this agent is reachable.
    version:
        Semantic version. Defaults to ``"1.0.0"``.
    protocol:
        Transport protocol. Defaults to ``"http"``.
    health_url:
        Optional health-check endpoint.
    estimated_latency_ms:
        Estimated response latency in milliseconds.
    include_function_capabilities:
        If ``True``, registered functions become capabilities.

    Returns
    -------
    AgentCard
        A validated AgentCard.
    """
    name: str = getattr(agent, "name", "AutoGen Agent")
    # Prefer explicit description; fall back to system_message
    desc: str = (
        getattr(agent, "description", None)
        or getattr(agent, "system_message", None)
        or f"AutoGen agent: {name}"
    )
    # Truncate description to 512 chars for AgentCard
    if len(desc) > 512:
        desc = desc[:509] + "..."

    primary_cap = Capability(
        id=_name_to_cap_id(name),
        description=desc,
        tags=["autogen", "agent"],
    )

    capabilities = [primary_cap]

    if include_function_capabilities:
        for fn_schema in _extract_functions(agent):
            fn_id = f"fn.{_name_to_cap_id(fn_schema['name'])}"
            fn_desc = fn_schema.get("description") or f"Function: {fn_schema['name']}"
            input_schema = None
            if fn_schema.get("parameters"):
                input_schema = fn_schema["parameters"]
            capabilities.append(
                Capability(
                    id=fn_id,
                    description=fn_desc,
                    input_schema=input_schema,
                )
            )

    pricing = None
    if estimated_latency_ms is not None:
        pricing = PricingModel(
            base_cost_joules=LANDAUER_FLOOR_JOULES,
            estimated_latency_ms=estimated_latency_ms,
        )

    card = AgentCard(
        agent_id=agent_id,
        name=name,
        version=version,
        capabilities=capabilities,
        endpoint=Endpoint(
            protocol=protocol,
            url=endpoint_url,
            health_url=health_url,
        ),
        pricing=pricing,
    )
    card.validate()
    return card


# ── GroupChat → list[AgentCard] ───────────────────────────────────────────────

def groupchat_to_agentcards(
    groupchat: "GroupChat",
    agent_ids: Optional[list[str]] = None,
    base_url: str = "https://localhost/api",
    *,
    version: str = "1.0.0",
    protocol: str = "http",
    include_function_capabilities: bool = True,
) -> list[AgentCard]:
    """
    Convert all agents in an AutoGen ``GroupChat`` to ``AgentCard`` objects.

    Parameters
    ----------
    groupchat:
        An AutoGen ``GroupChat`` instance.
    agent_ids:
        Optional list of 26-char ULIDs. If shorter than the agent count,
        remaining IDs are generated from hashed names (for local testing).
    base_url:
        Base URL prefix. Each agent URL = ``{base_url}/{agent_name}``.
    version:
        Semantic version for all cards.
    protocol:
        Transport protocol for all cards.
    include_function_capabilities:
        Whether to include function capabilities in each card.

    Returns
    -------
    list[AgentCard]
        One AgentCard per agent.
    """
    agents: list[Any] = getattr(groupchat, "agents", []) or []
    if not agents:
        raise ValueError("GroupChat has no agents")

    cards = []
    for i, agent in enumerate(agents):
        name = getattr(agent, "name", f"agent_{i}")
        slug = _name_to_cap_id(name)
        url = f"{base_url.rstrip('/')}/{slug}"

        if agent_ids and i < len(agent_ids):
            aid = agent_ids[i]
        else:
            import hashlib
            h = hashlib.sha256(name.encode()).hexdigest().upper()[:26]
            h = h.translate(str.maketrans("ILOU", "JKMN"))
            aid = h

        card = agent_to_agentcard(
            agent=agent,
            agent_id=aid,
            endpoint_url=url,
            version=version,
            protocol=protocol,
            include_function_capabilities=include_function_capabilities,
        )
        cards.append(card)

    return cards


# ── AgentCard → AutoGen tool function ────────────────────────────────────────

def agentcard_to_tool_function(
    card: AgentCard,
    capability_index: int = 0,
    timeout: float = 30.0,
) -> tuple[Callable[..., str], dict[str, Any]]:
    """
    Convert an AgentCard capability to an AutoGen-compatible tool function.

    Returns a ``(function, schema)`` tuple where:

    - ``function`` is a Python callable that POSTs to the card's endpoint.
    - ``schema`` is an OpenAI-compatible function schema dict suitable for
      passing to ``AssistantAgent`` via ``llm_config["functions"]`` or
      ``register_for_llm()``.

    Parameters
    ----------
    card:
        The source AgentCard.
    capability_index:
        Which capability to use. Defaults to 0.
    timeout:
        HTTP timeout in seconds.

    Returns
    -------
    tuple[Callable, dict]
        ``(fn, fn_schema)``

    Example
    -------
    ::

        fn, schema = agentcard_to_tool_function(card)
        assistant = AssistantAgent(
            name="assistant",
            llm_config={
                "model": "gpt-4o",
                "functions": [schema],
            },
        )
        assistant.register_for_execution(name=schema["name"])(fn)
    """
    cap = card.capabilities[capability_index]
    fn_name = cap.id.replace(".", "_").replace("-", "_")
    endpoint_url = card.endpoint.url

    def _remote_call(**kwargs: Any) -> str:
        import json as _json
        import urllib.request

        body = _json.dumps(kwargs).encode()
        headers = {"Content-Type": "application/json"}

        # Apply auth if present
        if card.endpoint.auth:
            auth = card.endpoint.auth
            if auth.scheme == "bearer" and auth.token_url:
                headers["Authorization"] = f"Bearer {auth.token_url}"
            elif auth.scheme == "api_key" and auth.header:
                headers[auth.header] = ""  # placeholder

        req = urllib.request.Request(endpoint_url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read().decode()

    _remote_call.__name__ = fn_name
    _remote_call.__doc__ = cap.description

    # Build OpenAI-compatible function schema
    parameters: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    if cap.input_schema:
        parameters = cap.input_schema

    fn_schema: dict[str, Any] = {
        "name": fn_name,
        "description": cap.description,
        "parameters": parameters,
    }

    return _remote_call, fn_schema


# ── AgentCardRegistry ─────────────────────────────────────────────────────────

class AgentCardRegistry:
    """
    An in-process registry of AgentCards for AutoGen multi-agent systems.

    Register all agents at startup; resolve AgentCard by name during
    conversation to route A2A calls with full identity context.

    Usage
    -----
    ::

        registry = AgentCardRegistry()
        registry.register(assistant_card)
        registry.register(researcher_card)

        # Resolve a peer's card during a conversation
        peer_card = registry.get("assistant")

        # Get all tool functions for use in function_map
        tool_map = registry.all_tool_functions()
    """

    def __init__(self) -> None:
        self._cards: dict[str, AgentCard] = {}  # keyed by agent_id
        self._by_name: dict[str, str] = {}       # name → agent_id

    def register(self, card: AgentCard) -> None:
        """Register an AgentCard."""
        card.validate()
        self._cards[card.agent_id] = card
        self._by_name[card.name.lower()] = card.agent_id

    def get_by_id(self, agent_id: str) -> Optional[AgentCard]:
        """Retrieve a card by ULID."""
        return self._cards.get(agent_id)

    def get(self, name: str) -> Optional[AgentCard]:
        """Retrieve a card by agent name (case-insensitive)."""
        aid = self._by_name.get(name.lower())
        return self._cards.get(aid) if aid else None

    def all_cards(self) -> list[AgentCard]:
        """Return all registered cards."""
        return list(self._cards.values())

    def all_tool_functions(
        self,
    ) -> dict[str, Callable[..., str]]:
        """
        Build a function_map from all registered cards (one fn per card).

        Suitable for passing to ``UserProxyAgent(function_map=...)``.
        """
        result: dict[str, Callable[..., str]] = {}
        for card in self._cards.values():
            fn, schema = agentcard_to_tool_function(card)
            result[schema["name"]] = fn
        return result

    def __len__(self) -> int:
        return len(self._cards)

    def __repr__(self) -> str:
        names = [c.name for c in self._cards.values()]
        return f"AgentCardRegistry({names!r})"
