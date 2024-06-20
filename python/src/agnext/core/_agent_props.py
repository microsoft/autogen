from typing import Protocol, Sequence, runtime_checkable

from ._agent_id import AgentId


@runtime_checkable
class AgentChildren(Protocol):
    @property
    def children(self) -> Sequence[AgentId]:
        """Ids of the children of the agent."""
        ...
