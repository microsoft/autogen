from typing import Sequence, TypedDict


class AgentMetadata(TypedDict):
    name: str
    description: str
    subscriptions: Sequence[type]
