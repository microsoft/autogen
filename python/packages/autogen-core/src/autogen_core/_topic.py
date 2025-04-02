import re
from dataclasses import dataclass

from typing_extensions import Self


def is_valid_topic_type(value: str) -> bool:
    return bool(re.match(r"^[\w\-\.\:\=]+\Z", value))


@dataclass(eq=True, frozen=True)
class TopicId:
    """
    TopicId defines the scope of a broadcast message. In essence, agent runtime implements a publish-subscribe model through its broadcast API: when publishing a message, the topic must be specified.

    See here for more information: :ref:`topic_and_subscription_topic`
    """

    type: str
    """Type of the event that this topic_id contains. Adhere's to the cloud event spec.

    Must match the pattern: ^[\\w\\-\\.\\:\\=]+\\Z

    Learn more here: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type
    """

    source: str
    """Identifies the context in which an event happened. Adhere's to the cloud event spec.

    Learn more here: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#source-1
    """

    def __post_init__(self) -> None:
        if is_valid_topic_type(self.type) is False:
            raise ValueError(f"Invalid topic type: {self.type}. Must match the pattern: ^[\\w\\-\\.\\:\\=]+\\Z")

    def __str__(self) -> str:
        return f"{self.type}/{self.source}"

    @classmethod
    def from_str(cls, topic_id: str) -> Self:
        """Convert a string of the format ``type/source`` into a TopicId"""
        items = topic_id.split("/", maxsplit=1)
        if len(items) != 2:
            raise ValueError(f"Invalid topic id: {topic_id}")
        type, source = items[0], items[1]
        return cls(type, source)
