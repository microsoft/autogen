"""AgentChat sample: persistent long-term memory via Synap.

[Synap](https://maximem.ai) is a managed long-term memory layer for AI agents.
The `synap-autogen` package exposes Synap as AutoGen `BaseTool` implementations
so an `AssistantAgent` can search and store memories across conversations.

Setup:
    pip install synap-autogen maximem-synap "autogen-agentchat" "autogen-ext[openai]"
    export SYNAP_API_KEY=<your-key>     # https://synap.maximem.ai
    export OPENAI_API_KEY=<your-key>

Run:
    python main.py

Open source integration package:
https://github.com/maximem-ai/maximem_synap_sdk/tree/main/packages/integrations/synap-autogen
"""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from maximem_synap import MaximemSynapSDK
from synap_autogen import SynapSearchTool, SynapStoreTool


async def main() -> None:
    sdk = MaximemSynapSDK(api_key=os.environ["SYNAP_API_KEY"])
    await sdk.initialize()

    user_id = "demo-user-001"
    customer_id = "demo-customer"

    tools = [
        SynapSearchTool(sdk=sdk, user_id=user_id, customer_id=customer_id),
        SynapStoreTool(sdk=sdk, user_id=user_id, customer_id=customer_id),
    ]

    agent = AssistantAgent(
        name="memory_assistant",
        model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"),
        tools=tools,
        system_message=(
            "You are a helpful assistant with long-term memory. "
            "Call synap_search to recall what you know about the user. "
            "Call synap_store to save important new facts."
        ),
    )

    await Console(
        agent.run_stream(
            task="I'm a software engineer who's allergic to peanuts. Remember this."
        )
    )

    await Console(
        agent.run_stream(task="What do you know about my dietary restrictions?")
    )


if __name__ == "__main__":
    asyncio.run(main())
