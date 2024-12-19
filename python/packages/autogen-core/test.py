from dataclasses import dataclass

from autogen_core.base import MessageContext
from autogen_core.base._agent_id import AgentId
from autogen_core.components import RoutedAgent
from autogen_core.components._routed_agent import rpc

from autogen_core.application import SingleThreadedAgentRuntime
import asyncio

@dataclass
class Message:
    content: str

class MyAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("My agent")

    @rpc
    async def handle_message(self, message: Message, ctx: MessageContext) -> Message:
        print(f"Received message: {message.content}")
        return Message(content=f"I got: {message.content}")

async def main():
    runtime = SingleThreadedAgentRuntime()

    await MyAgent.register(runtime, "my_agent", MyAgent)

    runtime.start()
    print(await runtime.send_message(
        Message("I'm sending you this"), recipient=AgentId("my_agent", "default")
    ))
    await runtime.stop_when_idle()

asyncio.run(main())
