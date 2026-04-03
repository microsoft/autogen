"""MnemoPay tools — agent memory + wallet for AutoGen.

Each tool is a :class:`BaseTool` subclass that communicates with the MnemoPay
MCP server over stdio (``npx -y @mnemopay/sdk``) using AutoGen's built-in
:class:`StdioMcpToolAdapter`.
"""

from __future__ import annotations

import os
from typing import Optional

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field

from ._config import MnemoPayConfig

# ---------------------------------------------------------------------------
# Lazy import helpers — mcp extra is optional
# ---------------------------------------------------------------------------

_MCP_IMPORT_ERROR = (
    "MnemoPay tools require the 'mcp' extra. "
    "Install it with: pip install \"autogen-ext[mnemopay]\""
)


def _get_server_params(config: MnemoPayConfig):  # type: ignore[return]
    """Build :class:`StdioServerParams` for the MnemoPay MCP server."""
    try:
        from autogen_ext.tools.mcp import StdioServerParams
    except ImportError as exc:
        raise ImportError(_MCP_IMPORT_ERROR) from exc

    env = {
        **os.environ,
        "MNEMOPAY_AGENT_ID": config.agent_id,
        "MNEMOPAY_MODE": config.mode,
    }
    return StdioServerParams(
        command=config.npx_command,
        args=["-y", "@mnemopay/sdk"],
        env=env,
    )


# ---------------------------------------------------------------------------
# Arg / Return models
# ---------------------------------------------------------------------------

# -- Memory --

class RememberArgs(BaseModel):
    content: str = Field(..., description="What to remember.")
    importance: Optional[float] = Field(
        default=None, description="Importance score 0-1. Auto-scored if omitted."
    )


class RememberReturn(BaseModel):
    result: str = Field(..., description="Confirmation with the stored memory ID.")


class RecallArgs(BaseModel):
    query: Optional[str] = Field(default=None, description="Semantic search query.")
    limit: int = Field(default=5, description="Maximum number of memories to return.")


class RecallReturn(BaseModel):
    result: str = Field(..., description="Matching memories as JSON.")


class ForgetArgs(BaseModel):
    id: str = Field(..., description="Memory ID to permanently delete.")


class ForgetReturn(BaseModel):
    result: str = Field(..., description="Confirmation of deletion.")


class ReinforceArgs(BaseModel):
    id: str = Field(..., description="Memory ID to reinforce.")
    boost: float = Field(default=0.1, description="Importance boost 0.01-0.5.")


class ReinforceReturn(BaseModel):
    result: str = Field(..., description="Updated importance score.")


class ConsolidateArgs(BaseModel):
    pass


class ConsolidateReturn(BaseModel):
    result: str = Field(..., description="Number of stale memories pruned.")


# -- Wallet --

class ChargeArgs(BaseModel):
    amount: float = Field(..., description="Amount in USD to charge.")
    reason: str = Field(..., description="Description of value delivered.")


class ChargeReturn(BaseModel):
    result: str = Field(..., description="Transaction ID and escrow status.")


class SettleArgs(BaseModel):
    tx_id: str = Field(..., description="Transaction ID to finalize.")


class SettleReturn(BaseModel):
    result: str = Field(..., description="Settlement confirmation. Reputation +0.01.")


class RefundArgs(BaseModel):
    tx_id: str = Field(..., description="Transaction ID to refund.")


class RefundReturn(BaseModel):
    result: str = Field(..., description="Refund confirmation. Reputation -0.05.")


class BalanceArgs(BaseModel):
    pass


class BalanceReturn(BaseModel):
    result: str = Field(..., description="Wallet balance and reputation score.")


class ProfileArgs(BaseModel):
    pass


class ProfileReturn(BaseModel):
    result: str = Field(..., description="Full agent stats: reputation, wallet, memory count, tx count.")


class HistoryArgs(BaseModel):
    limit: int = Field(default=10, description="Number of transactions to return.")


class HistoryReturn(BaseModel):
    result: str = Field(..., description="Recent transactions as JSON.")


class LogsArgs(BaseModel):
    limit: int = Field(default=20, description="Number of log entries to return.")


class LogsReturn(BaseModel):
    result: str = Field(..., description="Immutable audit trail entries as JSON.")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

class _MnemoPayMixin:
    """Shared MCP-client logic for all MnemoPay tools.

    This is a mixin — concrete tool classes inherit from both this and
    ``BaseTool[ArgsT, ReturnT]``.  Each subclass sets ``_mcp_tool_name``
    and ``_config``.
    """

    _mcp_tool_name: str
    _config: MnemoPayConfig

    async def _call_mcp(self, arguments: dict) -> str:
        """Spawn a one-shot MCP session and call the tool."""
        try:
            from autogen_ext.tools.mcp import StdioServerParams  # noqa: F401
            from autogen_ext.tools.mcp._session import create_mcp_server_session
        except ImportError as exc:
            raise ImportError(_MCP_IMPORT_ERROR) from exc

        server_params = _get_server_params(self._config)
        async with create_mcp_server_session(server_params) as session:
            await session.initialize()
            result = await session.call_tool(name=self._mcp_tool_name, arguments=arguments)
            content = result.content
            if content and isinstance(content, list):
                first = content[0]
                if hasattr(first, "text"):
                    return first.text  # type: ignore[union-attr]
                return str(first)
            return str(result)


class RememberTool(_MnemoPayMixin, BaseTool[RememberArgs, RememberReturn]):
    """Store a memory that persists across agent sessions.

    Memories are scored by importance and decay over time.  Agents can later
    retrieve them with :class:`RecallTool`.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"

    Example usage with AssistantAgent:

    .. code-block:: python

        import asyncio
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.tools.mnemopay import RememberTool, RecallTool, MnemoPayConfig
        from autogen_agentchat.agents import AssistantAgent

        async def main():
            config = MnemoPayConfig(agent_id="research-bot")
            agent = AssistantAgent(
                name="researcher",
                tools=[RememberTool(config), RecallTool(config)],
                model_client=OpenAIChatCompletionClient(model="gpt-4o"),
            )
            result = await agent.run(task="Remember that the user prefers dark mode.")
            print(result.messages[-1])

        asyncio.run(main())
    """

    _mcp_tool_name = "remember"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=RememberArgs,
            return_type=RememberReturn,
            name="mnemopay_remember",
            description="Store a memory that persists across sessions.",
        )

    async def run(self, args: RememberArgs, cancellation_token: CancellationToken) -> RememberReturn:
        arguments: dict = {"content": args.content}
        if args.importance is not None:
            arguments["importance"] = args.importance
        result = await self._call_mcp(arguments)
        return RememberReturn(result=result)


class RecallTool(_MnemoPayMixin, BaseTool[RecallArgs, RecallReturn]):
    """Recall relevant memories via semantic search.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "recall"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=RecallArgs,
            return_type=RecallReturn,
            name="mnemopay_recall",
            description="Recall relevant memories. Supports semantic search.",
        )

    async def run(self, args: RecallArgs, cancellation_token: CancellationToken) -> RecallReturn:
        arguments: dict = {"limit": args.limit}
        if args.query:
            arguments["query"] = args.query
        result = await self._call_mcp(arguments)
        return RecallReturn(result=result)


class ForgetTool(_MnemoPayMixin, BaseTool[ForgetArgs, ForgetReturn]):
    """Permanently delete a memory by ID.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "forget"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=ForgetArgs,
            return_type=ForgetReturn,
            name="mnemopay_forget",
            description="Permanently delete a memory by ID.",
        )

    async def run(self, args: ForgetArgs, cancellation_token: CancellationToken) -> ForgetReturn:
        result = await self._call_mcp({"id": args.id})
        return ForgetReturn(result=result)


class ReinforceTool(_MnemoPayMixin, BaseTool[ReinforceArgs, ReinforceReturn]):
    """Boost a memory's importance score after it proved valuable.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "reinforce"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=ReinforceArgs,
            return_type=ReinforceReturn,
            name="mnemopay_reinforce",
            description="Boost a memory's importance after it proved valuable.",
        )

    async def run(self, args: ReinforceArgs, cancellation_token: CancellationToken) -> ReinforceReturn:
        result = await self._call_mcp({"id": args.id, "boost": args.boost})
        return ReinforceReturn(result=result)


class ConsolidateTool(_MnemoPayMixin, BaseTool[ConsolidateArgs, ConsolidateReturn]):
    """Prune stale memories that have decayed below threshold.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "consolidate"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=ConsolidateArgs,
            return_type=ConsolidateReturn,
            name="mnemopay_consolidate",
            description="Prune stale memories below decay threshold.",
        )

    async def run(self, args: ConsolidateArgs, cancellation_token: CancellationToken) -> ConsolidateReturn:
        result = await self._call_mcp({})
        return ConsolidateReturn(result=result)


class ChargeTool(_MnemoPayMixin, BaseTool[ChargeArgs, ChargeReturn]):
    """Create an escrow charge for work the agent delivered.

    The charge is held in escrow until :class:`SettleTool` finalizes it or
    :class:`RefundTool` reverses it.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"

    Example usage with AssistantAgent:

    .. code-block:: python

        import asyncio
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_ext.tools.mnemopay import ChargeTool, SettleTool, BalanceTool, MnemoPayConfig
        from autogen_agentchat.agents import AssistantAgent

        async def main():
            config = MnemoPayConfig(agent_id="billing-bot")
            agent = AssistantAgent(
                name="billing_agent",
                tools=[ChargeTool(config), SettleTool(config), BalanceTool(config)],
                model_client=OpenAIChatCompletionClient(model="gpt-4o"),
            )
            result = await agent.run(task="Charge $0.50 for the research report I just completed.")
            print(result.messages[-1])

        asyncio.run(main())
    """

    _mcp_tool_name = "charge"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=ChargeArgs,
            return_type=ChargeReturn,
            name="mnemopay_charge",
            description="Create an escrow charge for work delivered.",
        )

    async def run(self, args: ChargeArgs, cancellation_token: CancellationToken) -> ChargeReturn:
        result = await self._call_mcp({"amount": args.amount, "reason": args.reason})
        return ChargeReturn(result=result)


class SettleTool(_MnemoPayMixin, BaseTool[SettleArgs, SettleReturn]):
    """Finalize a pending escrow charge. Boosts agent reputation by +0.01.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "settle"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=SettleArgs,
            return_type=SettleReturn,
            name="mnemopay_settle",
            description="Finalize a pending escrow. Boosts reputation +0.01.",
        )

    async def run(self, args: SettleArgs, cancellation_token: CancellationToken) -> SettleReturn:
        result = await self._call_mcp({"txId": args.tx_id})
        return SettleReturn(result=result)


class RefundTool(_MnemoPayMixin, BaseTool[RefundArgs, RefundReturn]):
    """Refund a transaction. Docks agent reputation by -0.05.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "refund"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=RefundArgs,
            return_type=RefundReturn,
            name="mnemopay_refund",
            description="Refund a transaction. Docks reputation -0.05.",
        )

    async def run(self, args: RefundArgs, cancellation_token: CancellationToken) -> RefundReturn:
        result = await self._call_mcp({"txId": args.tx_id})
        return RefundReturn(result=result)


class BalanceTool(_MnemoPayMixin, BaseTool[BalanceArgs, BalanceReturn]):
    """Check the agent's wallet balance and reputation score.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "balance"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=BalanceArgs,
            return_type=BalanceReturn,
            name="mnemopay_balance",
            description="Check wallet balance and reputation score.",
        )

    async def run(self, args: BalanceArgs, cancellation_token: CancellationToken) -> BalanceReturn:
        result = await self._call_mcp({})
        return BalanceReturn(result=result)


class ProfileTool(_MnemoPayMixin, BaseTool[ProfileArgs, ProfileReturn]):
    """Full agent stats: reputation, wallet, memory count, transaction count.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "profile"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=ProfileArgs,
            return_type=ProfileReturn,
            name="mnemopay_profile",
            description="Full agent stats: reputation, wallet, memory count, tx count.",
        )

    async def run(self, args: ProfileArgs, cancellation_token: CancellationToken) -> ProfileReturn:
        result = await self._call_mcp({})
        return ProfileReturn(result=result)


class HistoryTool(_MnemoPayMixin, BaseTool[HistoryArgs, HistoryReturn]):
    """Transaction history, most recent first.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "history"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=HistoryArgs,
            return_type=HistoryReturn,
            name="mnemopay_history",
            description="Transaction history, most recent first.",
        )

    async def run(self, args: HistoryArgs, cancellation_token: CancellationToken) -> HistoryReturn:
        result = await self._call_mcp({"limit": args.limit})
        return HistoryReturn(result=result)


class LogsTool(_MnemoPayMixin, BaseTool[LogsArgs, LogsReturn]):
    """Immutable audit trail of all agent actions.

    .. note::

        This tool requires the :code:`mnemopay` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[mnemopay]"
    """

    _mcp_tool_name = "logs"

    def __init__(self, config: MnemoPayConfig | None = None) -> None:
        self._config = config or MnemoPayConfig()
        super().__init__(
            args_type=LogsArgs,
            return_type=LogsReturn,
            name="mnemopay_logs",
            description="Immutable audit trail of all actions.",
        )

    async def run(self, args: LogsArgs, cancellation_token: CancellationToken) -> LogsReturn:
        result = await self._call_mcp({"limit": args.limit})
        return LogsReturn(result=result)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def mnemopay_tools(config: MnemoPayConfig | None = None) -> list[BaseTool]:  # type: ignore[type-arg]
    """Return all 13 MnemoPay tools ready to pass to an AutoGen agent.

    .. code-block:: python

        from autogen_ext.tools.mnemopay import mnemopay_tools, MnemoPayConfig
        from autogen_agentchat.agents import AssistantAgent

        tools = mnemopay_tools(MnemoPayConfig(agent_id="my-agent"))
        agent = AssistantAgent(name="agent", tools=tools, ...)

    Args:
        config: Optional :class:`MnemoPayConfig`.  Defaults are used when ``None``.

    Returns:
        A list of all 13 MnemoPay :class:`BaseTool` instances.
    """
    cfg = config or MnemoPayConfig()
    return [
        # Memory
        RememberTool(cfg),
        RecallTool(cfg),
        ForgetTool(cfg),
        ReinforceTool(cfg),
        ConsolidateTool(cfg),
        # Wallet
        ChargeTool(cfg),
        SettleTool(cfg),
        RefundTool(cfg),
        # Info
        BalanceTool(cfg),
        ProfileTool(cfg),
        HistoryTool(cfg),
        LogsTool(cfg),
    ]
