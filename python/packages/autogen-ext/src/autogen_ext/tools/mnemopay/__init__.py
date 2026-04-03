"""MnemoPay tools for AutoGen — persistent agent memory + micropayment wallet.

`MnemoPay <https://mnemopay.com>`_ gives AI agents two primitives that survive
across sessions:

* **Memory** — store, recall, reinforce, and prune knowledge.
* **Wallet** — charge for work, settle/refund via escrow, track reputation.

Under the hood each tool talks to the MnemoPay MCP server
(``npx -y @mnemopay/sdk``) over stdio.

Quick start
-----------

.. code-block:: bash

    pip install -U "autogen-ext[mnemopay]"

.. code-block:: python

    import asyncio
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.tools.mnemopay import mnemopay_tools, MnemoPayConfig
    from autogen_agentchat.agents import AssistantAgent

    async def main():
        config = MnemoPayConfig(agent_id="research-bot")
        agent = AssistantAgent(
            name="researcher",
            tools=mnemopay_tools(config),
            model_client=OpenAIChatCompletionClient(model="gpt-4o"),
            system_message=(
                "You are a research assistant with persistent memory and a wallet. "
                "Use mnemopay_remember to save important findings and "
                "mnemopay_recall to retrieve them. Use mnemopay_charge when you "
                "deliver valuable work."
            ),
        )
        result = await agent.run(
            task="Remember that the user's favourite framework is AutoGen."
        )
        print(result.messages[-1])

    asyncio.run(main())
"""

from ._config import MnemoPayConfig
from ._tools import (
    BalanceArgs,
    BalanceReturn,
    BalanceTool,
    ChargeArgs,
    ChargeReturn,
    ChargeTool,
    ConsolidateArgs,
    ConsolidateReturn,
    ConsolidateTool,
    ForgetArgs,
    ForgetReturn,
    ForgetTool,
    HistoryArgs,
    HistoryReturn,
    HistoryTool,
    LogsArgs,
    LogsReturn,
    LogsTool,
    ProfileArgs,
    ProfileReturn,
    ProfileTool,
    RecallArgs,
    RecallReturn,
    RecallTool,
    RefundArgs,
    RefundReturn,
    RefundTool,
    ReinforceArgs,
    ReinforceReturn,
    ReinforceTool,
    RememberArgs,
    RememberReturn,
    RememberTool,
    SettleArgs,
    SettleReturn,
    SettleTool,
    mnemopay_tools,
)

__all__ = [
    # Config
    "MnemoPayConfig",
    # Factory
    "mnemopay_tools",
    # Memory tools
    "RememberTool",
    "RememberArgs",
    "RememberReturn",
    "RecallTool",
    "RecallArgs",
    "RecallReturn",
    "ForgetTool",
    "ForgetArgs",
    "ForgetReturn",
    "ReinforceTool",
    "ReinforceArgs",
    "ReinforceReturn",
    "ConsolidateTool",
    "ConsolidateArgs",
    "ConsolidateReturn",
    # Wallet tools
    "ChargeTool",
    "ChargeArgs",
    "ChargeReturn",
    "SettleTool",
    "SettleArgs",
    "SettleReturn",
    "RefundTool",
    "RefundArgs",
    "RefundReturn",
    # Info tools
    "BalanceTool",
    "BalanceArgs",
    "BalanceReturn",
    "ProfileTool",
    "ProfileArgs",
    "ProfileReturn",
    "HistoryTool",
    "HistoryArgs",
    "HistoryReturn",
    "LogsTool",
    "LogsArgs",
    "LogsReturn",
]
