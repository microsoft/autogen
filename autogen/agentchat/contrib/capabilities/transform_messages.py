import copy
import sys
from typing import Any, Dict, List, Optional, Protocol, Union

import tiktoken
from termcolor import colored

from autogen import ConversableAgent, token_count_utils


class MessageTransform(Protocol):
    """Defines a contract for message transformation.

    Classes implementing this protocol should provide an `apply_transform` method
    that takes a list of messages and returns the transformed list.
    """

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """Applies a transformation to a list of messages.

        Args:
            messages: A list of dictionaries representing messages.

        Returns:
            A new list of dictionaries containing the transformed messages.
        """
        ...


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

    def __init__(self, *, transforms: List[MessageTransform] = []):
        """
        Args:
            transforms: A list of message transformations to apply.
        """
        self._transforms = transforms

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
            temp_messages = transform.apply_transform(temp_messages)

        if system_message:
            temp_messages.insert(0, system_message)

        self._print_stats(messages, temp_messages)

        return temp_messages

    def _print_stats(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]):
        pre_transform_messages_len = len(pre_transform_messages)
        post_transform_messages_len = len(post_transform_messages)

        if pre_transform_messages_len < post_transform_messages_len:
            print(
                colored(
                    f"Number of messages reduced from {pre_transform_messages_len} to {post_transform_messages_len}.",
                    "yellow",
                )
            )


class MessageHistoryLimiter:
    """Limits the number of messages considered by an agent for response generation.

    This transform is handy when you want to limit the conversational context to a specific number of recent messages,
    ensuring efficient processing and response generation.
    """

    def __init__(self, max_messages: Optional[int] = None):
        """
        Args:
            max_messages (None or int): Maximum number of messages to keep in the context.
            Must be greater than 0 if not None.
        """
        self._validate_max_messages(max_messages)
        self._max_messages = max_messages if max_messages else sys.maxsize

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """This method returns a new list containing the most recent messages up to the specified
        maximum number of messages (max_messages). If max_messages is `None`,
        it returns the original list of messages unmodified.

        Args:
            messages (List[Dict]): The list of messages representing the conversation history.

        Returns:
            List[Dict]: A new list containing the most recent messages up to the specified maximum.
        """
        if self._max_messages is None:
            return messages

        return messages[-self._max_messages :]

    def _validate_max_messages(self, max_messages: Optional[int]):
        if max_messages is not None and max_messages < 1:
            raise ValueError("max_messages must be None or greater than 1")


class MessageTokenLimiter:
    """Truncates messages to meet token limits for efficient processing and response generation.

    Truncation can be applied to individual messages or the entire conversation history.

    This transformation is handy when you need to adhere to strict token limits imposed by your API provider,
    preventing unnecessary costs or errors caused by exceeding the allowed token count.
    """

    def __init__(
        self,
        max_tokens_per_message: Optional[int] = None,
        max_tokens: Optional[int] = None,
        model: str = "gpt-3.5-turbo-0613",
    ):
        """
        Args:
            max_tokens_per_message (None or int): Maximum number of tokens to keep in each message.
                Must be greater than or equal to 0 if not None.
            max_tokens (Optional[int]): Maximum number of tokens to keep in the chat history.
                Must be greater than or equal to 0 if not None.
            model (str): The target OpenAI model for tokenization alignment.
        """
        self._validate_max_tokens(max_tokens_per_message)
        self._validate_max_tokens(max_tokens)

        self._max_tokens_per_message = max_tokens_per_message if max_tokens_per_message else sys.maxsize
        self._max_tokens = max_tokens if max_tokens else sys.maxsize
        self._model = model

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        """This method applies two levels of truncation:

        1. Truncates each individual message to the max number of tokens (max_tokens_per_message).
        2. Truncates the overall conversation history to max number of tokens (max_tokens).

        Messages are processed in reverse order, and the truncated conversation history is
        reconstructed by appending messages to the beginning of the list to preserve order.

        If the total number of tokens in the original conversation history exceeds the
        number of tokens in the truncated history, a warning message is printed indicating
        the number of tokens reduced.

        Args:
            messages (List[Dict]): The list of messages representing the conversation history.

        Returns:
            List[Dict]: A new list containing the truncated messages up to the specified token limits.
        """
        assert self._max_tokens_per_message is not None
        assert self._max_tokens is not None

        temp_messages = messages.copy()
        processed_messages = []
        processed_messages_tokens = 0

        # calculate tokens for all messages
        total_tokens = sum(_count_tokens(msg["content"]) for msg in temp_messages)

        for msg in reversed(temp_messages):
            msg["content"] = self._truncate_str_to_tokens(msg["content"])
            msg_tokens = _count_tokens(msg["content"])

            if processed_messages_tokens + msg_tokens > self._max_tokens:
                break

            # append the message to the beginning of the list to preserve order
            processed_messages_tokens += msg_tokens
            processed_messages.insert(0, msg)

        if total_tokens > processed_messages_tokens:
            print(
                colored(
                    f"Truncated {total_tokens - processed_messages_tokens} tokens. Tokens reduced from {total_tokens} to {processed_messages_tokens}",
                    "yellow",
                )
            )

        return processed_messages

    def _truncate_str_to_tokens(self, contents: Union[str, List]):
        if isinstance(contents, str):
            return self._truncate_tokens(contents)
        elif isinstance(contents, list):
            return self._truncate_multimodal_text(contents)
        else:
            raise ValueError(f"Contents must be a string or a list of dictionaries. Received type: {type(contents)}")

    def _truncate_multimodal_text(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tmp_contents = []
        for content in contents:
            if content["type"] == "text":
                truncated_text = self._truncate_tokens(content["text"])
                tmp_contents.append({"type": "text", "text": truncated_text})
            else:
                tmp_contents.append(content)
        return tmp_contents

    def _truncate_tokens(self, text: str):
        encoding = tiktoken.encoding_for_model(self._model)  # Get the appropriate tokenizer

        encoded_tokens = encoding.encode(text)
        truncated_tokens = encoded_tokens[: self._max_tokens_per_message]
        truncated_text = encoding.decode(truncated_tokens)  # Decode back to text

        return truncated_text

    def _validate_max_tokens(self, max_tokens: Optional[int] = None):
        if max_tokens is not None and max_tokens < 0:
            raise ValueError("max_tokens and max_tokens_per_message must be None or greater than or equal to 0")


def _count_tokens(content: Union[str, List[Dict[str, Any]]]) -> int:
    token_count = 0
    if isinstance(content, str):
        token_count = token_count_utils.count_token(content)
    elif isinstance(content, list):
        for item in content:
            token_count += _count_tokens(item.get("text", ""))
    return token_count
