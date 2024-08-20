from dataclasses import dataclass


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
