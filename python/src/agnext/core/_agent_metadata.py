from typing import Sequence, TypedDict


class AgentMetadata(TypedDict):
    type: str
    key: str
    description: str
    subscriptions: Sequence[str]
