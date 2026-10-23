"""Requester agent for the Pilot Protocol AutoGen transport sample.

Sends a Greeting to the responder agent over a Pilot Protocol stream
connection and prints the reply. Run run_responder.py first.
"""

import asyncio

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from pilot_transport import Greeting, send_and_wait


class RequesterAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Sends a greeting over Pilot Protocol and prints the reply")

    @message_handler
    async def on_reply(self, message: Greeting, ctx: MessageContext) -> None:
        print(f"[requester] got reply: {message.text!r}")


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    await RequesterAgent.register(runtime, "requester", lambda: RequesterAgent())
    runtime.start()

    greeting = Greeting(sender="autogen-requester", text="hello from the requester")
    print(f"[requester] sending: {greeting.text!r}")
    reply = send_and_wait("autogen-responder", greeting)

    await runtime.send_message(reply, AgentId("requester", "default"))
    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
