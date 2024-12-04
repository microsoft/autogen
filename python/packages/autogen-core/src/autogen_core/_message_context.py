from dataclasses import dataclass

from ._agent_id import AgentId
from ._cancellation_token import CancellationToken
from ._topic import TopicId


@dataclass
class MessageContext:
    sender: AgentId | None
    topic_id: TopicId | None
    is_rpc: bool
    cancellation_token: CancellationToken
    message_id: str
