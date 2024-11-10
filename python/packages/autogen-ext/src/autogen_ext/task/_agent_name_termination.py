from typing import Sequence

from autogen_agentchat.base import TerminationCondition, TerminatedException
from autogen_agentchat.messages import StopMessage, AgentMessage, ChatMessage


class AgentNameTermination(TerminationCondition):
    """Terminate the conversation after a specific agent responds.

    Args:
        agent_name (str): The name of the agent whose response will trigger the termination.

    Raises:
        TerminatedException: If the termination condition has already been reached.
    """

    def __init__(self, agent_name: str) -> None:
        self._agent_name = agent_name
        self._terminated = False

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[AgentMessage]) -> StopMessage | None:
        if self._terminated:
            raise TerminatedException("Termination condition has already been reached")
        if not messages:
            return None
        last_message = messages[-1]
        if last_message.source == self._agent_name:
            if isinstance(last_message, ChatMessage):
                self._terminated = True
                return StopMessage(content=f"Agent '{self._agent_name}' answered", source="AgentNameTermination")
        return None

    async def reset(self) -> None:
        self._terminated = False
