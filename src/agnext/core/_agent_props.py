from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class AgentChildren(Protocol):
    @property
    def children(self) -> Sequence[str]:
        """Names of the children of the agent."""
        ...
