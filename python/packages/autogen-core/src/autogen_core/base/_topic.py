from dataclasses import dataclass

from typing_extensions import Self


@dataclass(eq=True, frozen=True)
class TopicId:
    type: str
    """Type of the event that this topic_id contains. Adhere's to the cloud event spec.

    Learn more here: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#type
    """

    source: str
    """Identifies the context in which an event happened. Adhere's to the cloud event spec.

    Learn more here: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#source-1
    """

    def __str__(self) -> str:
        return f"{self.type}/{self.source}"

    @classmethod
    def from_str(cls, topic_id: str) -> Self:
        items = topic_id.split("/", maxsplit=1)
        if len(items) != 2:
            raise ValueError(f"Invalid topic id: {topic_id}")
        type, source = items[0], items[1]
        return cls(type, source)
