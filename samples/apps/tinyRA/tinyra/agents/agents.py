import asyncio
from typing import Protocol, List


class AgentManager(Protocol):

    async def generate_response(self, message: str) -> str:
        pass


class ReversedAgents:

    async def generate_response(self, message: str) -> str:

        # sleep for a random amount of time
        # this is to simulate a long running task
        await asyncio.sleep(0.5)

        reversed_message = message[::-1]

        return reversed_message
