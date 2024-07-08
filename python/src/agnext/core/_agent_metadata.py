from typing import Sequence, TypedDict


class AgentMetadata(TypedDict):
    name: str
    namespace: str
    description: str
    subscriptions: Sequence[str]
