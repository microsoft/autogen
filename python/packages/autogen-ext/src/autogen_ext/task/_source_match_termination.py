from typing import Sequence, List

from autogen_agentchat.base import TerminationCondition, TerminatedException
from autogen_agentchat.messages import StopMessage, AgentMessage


class SourceMatchTermination(TerminationCondition):
    """Terminate the conversation after a specific source responds.

    Args:
        sources (List[str]): List of source names to terminate the conversation.

    Raises:
        TerminatedException: If the termination condition has already been reached.
    """

    def __init__(self, sources: List[str]) -> None:
        self._sources = sources
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
        if last_message.source in self._sources:
            self._terminated = True
            return StopMessage(content=f"'{last_message.source}' answered", source="SourceMatchTermination")
        return None

    async def reset(self) -> None:
        self._terminated = False
