from ..base import MessageHandlerContext, TopicId


class DefaultTopicId(TopicId):
    def __init__(self, type: str = "default", source: str | None = None) -> None:
        """DefaultTopicId provides a sensible default for the topic_id and source fields of a TopicId.

        If created in the context of a message handler, the source will be set to the agent_id of the message handler, otherwise it will be set to "default".

        Args:
            type (str, optional): Topic type to publish message to. Defaults to "default".
            source (str | None, optional): Topic source to publish message to. If None, the source will be set to the agent_id of the message handler if in the context of a message handler, otherwise it will be set to "default". Defaults to None.
        """
        if source is None:
            try:
                source = MessageHandlerContext.agent_id().key
            # If we aren't in the context of a message handler, we use the default source
            except RuntimeError:
                source = "default"

        super().__init__(type, source)
