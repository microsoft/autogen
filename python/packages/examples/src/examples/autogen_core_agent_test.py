

from dataclasses import dataclass
from typing import Any
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import BaseAgent,AgentId, MessageContext



@dataclass
class DemoMessage:
    content:str

@dataclass
class PublisTest:
    content:str

class AgentOne(BaseAgent):
    def __init__(self, description: str = "AgentOne"):
        super().__init__(description)
    

    async def on_message(self, message: DemoMessage, ctx: MessageContext) -> Any:
        print(f"接收到的消息是 》〉》〉{ctx}")


async def main():
    runtime = SingleThreadedAgentRuntime()
    agentType = await AgentOne.register(runtime,"myAgent",
                      lambda:AgentOne("我只是一个demo的代理"))
    print(f"Agent = {agentType}")
    runtime.start()
    await runtime.send_message(PublisTest(content="你好，世界！"), AgentId("myAgent","111"))
    await runtime.stop()
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
