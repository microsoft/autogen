"""Responder agent for the Pilot Protocol AutoGen transport sample.

Run this first, then run_requester.py from another terminal (or another
machine with mutual trust established -- see README.md).
"""

import asyncio

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from pilot_transport import Greeting, serve_once


class ResponderAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("Responds to greetings received over Pilot Protocol")

    @message_handler
    async def on_greeting(self, message: Greeting, ctx: MessageContext) -> Greeting:
        print(f"[responder] received: {message.text!r} from {message.sender}")
        return Greeting(sender="autogen-responder", text=f"hello back, {message.sender}")


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    await ResponderAgent.register(runtime, "responder", lambda: ResponderAgent())
    runtime.start()

    print("[responder] waiting for a Pilot Protocol connection on port 5000...")
    greeting, conn = serve_once()

    reply = await runtime.send_message(greeting, AgentId("responder", "default"))
    conn.write(reply.encode())
    conn.close()

    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
