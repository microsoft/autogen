"""
AutoGen Core Quick Start Example

Demonstrates the core agent runtime and messaging APIs with two simple agents: Modifier and Checker.
- Modifier agent decrements a number
- Checker agent checks if the number is above 1 and continues or stops
- Uses SingleThreadedAgentRuntime for local agent orchestration

Run: python core_quickstart_example.py
"""
import asyncio
from dataclasses import dataclass
from typing import Callable
from autogen_core import DefaultTopicId, MessageContext, RoutedAgent, default_subscription, message_handler, AgentId, SingleThreadedAgentRuntime

@dataclass
class Message:
    content: int

@default_subscription
class Modifier(RoutedAgent):
    def __init__(self, modify_val: Callable[[int], int]) -> None:
        super().__init__("A modifier agent.")
        self._modify_val = modify_val

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        val = self._modify_val(message.content)
        print(f"{'-'*80}\nModifier:\nModified {message.content} to {val}")
        await self.publish_message(Message(content=val), DefaultTopicId())  # type: ignore

@default_subscription
class Checker(RoutedAgent):
    def __init__(self, run_until: Callable[[int], bool]) -> None:
        super().__init__("A checker agent.")
        self._run_until = run_until

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        if not self._run_until(message.content):
            print(f"{'-'*80}\nChecker:\n{message.content} passed the check, continue.")
            await self.publish_message(Message(content=message.content), DefaultTopicId())
        else:
            print(f"{'-'*80}\nChecker:\n{message.content} failed the check, stopping.")

async def main() -> None:
    # Create a local embedded runtime.
    runtime = SingleThreadedAgentRuntime()

    # Register the modifier and checker agents
    await Modifier.register(
        runtime,
        "modifier",
        lambda: Modifier(modify_val=lambda x: x - 1),
    )
    await Checker.register(
        runtime,
        "checker",
        lambda: Checker(run_until=lambda x: x <= 1),
    )

    # Start the runtime and send a direct message to the checker.
    runtime.start()
    await runtime.send_message(Message(10), AgentId("checker", "default"))
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
