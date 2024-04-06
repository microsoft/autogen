import copy
from typing import Dict, List

from termcolor import colored

from autogen import ConversableAgent

from .transforms import MessageTransform


class TransformMessages:
    """Agent capability for transforming messages before reply generation.

    This capability allows you to apply a series of message transformations to
    a ConversableAgent's incoming messages before they are processed for response
    generation. This is useful for tasks such as:

    - Limiting the number of messages considered for context.
    - Truncating messages to meet token limits.
    - Filtering sensitive information.
    - Customizing message formatting.

    To use `TransformMessages`:

    1. Create message transformations (e.g., `MessageHistoryLimiter`, `MessageTokenLimiter`).
    2. Instantiate `TransformMessages` with a list of these transformations.
    3. Add the `TransformMessages` instance to your `ConversableAgent` using `add_to_agent`.

    NOTE: Order of message transformations is important. You could get different results based on
        the order of transformations.

    Example:
        ```python
        from agentchat import ConversableAgent
        from agentchat.contrib.capabilities import TransformMessages, MessageHistoryLimiter, MessageTokenLimiter

        max_messages = MessageHistoryLimiter(max_messages=2)
        truncate_messages = MessageTokenLimiter(max_tokens=500)
        transform_messages = TransformMessages(transforms=[max_messages, truncate_messages])

        agent = ConversableAgent(...)
        transform_messages.add_to_agent(agent)
        ```
    """

    def __init__(self, *, transforms: List[MessageTransform] = [], to_print_stats: bool = True):
        """
        Args:
            transforms: A list of message transformations to apply.
            to_print_stats: Whether to print stats of each transformation or not.
        """
        self._transforms = transforms
        self._to_print_stats = to_print_stats

    def add_to_agent(self, agent: ConversableAgent):
        """Adds the message transformations capability to the specified ConversableAgent.

        This function performs the following modifications to the agent:

        1. Registers a hook that automatically transforms all messages before they are processed for
            response generation.
        """
        agent.register_hook(hookable_method="process_all_messages_before_reply", hook=self._transform_messages)

    def _transform_messages(self, messages: List[Dict]) -> List[Dict]:
        temp_messages = copy.deepcopy(messages)
        system_message = None

        if messages[0]["role"] == "system":
            system_message = copy.deepcopy(messages[0])
            temp_messages.pop(0)

        for transform in self._transforms:
            if self._to_print_stats:
                pre_transform_messages = copy.deepcopy(temp_messages)
                temp_messages = transform.apply_transform(temp_messages)
                transform.print_stats(pre_transform_messages, temp_messages)
            else:
                temp_messages = transform.apply_transform(temp_messages)

        if system_message:
            temp_messages.insert(0, system_message)

        return temp_messages
