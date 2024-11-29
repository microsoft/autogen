import asyncio
from dataclasses import dataclass

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentRuntime, MessageContext
from autogen_core.components import ClosureAgent, DefaultSubscription, DefaultTopicId


@dataclass
class FinalResult:
    value: str


queue = asyncio.Queue[FinalResult]()
async def output_result(_runtime: AgentRuntime, id: AgentId, message: FinalResult, ctx: MessageContext) -> None:
    await queue.put(message)


runtime = SingleThreadedAgentRuntime()
async def run():
    await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [DefaultSubscription()])
    runtime.start()
    await runtime.publish_message(FinalResult("Result 1"), DefaultTopicId())
    await runtime.publish_message(FinalResult("Result 2"), DefaultTopicId())
    await runtime.stop_when_idle()

    while not queue.empty():
        print((result := await queue.get()).value)

if __name__=='__main__':
    asyncio.run(run())