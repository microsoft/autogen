import sys
from termcolor import colored
from typing import Dict, Optional, Union, List, Tuple, Any
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen import ConversableAgent
from autogen import token_count_utils


class LongContextCapability:
    """Base class for composable capabilities that can be added to an agent.

    Note about this capability:
        - this does not modify the agents chat history permanently
        - the processing happen every invocation
    """

    def __init__(self, max_messages: int = sys.maxsize, max_tokens: int = sys.maxsize):
        """
        Create a new context handling capability.

        Args:
            max_messages: Maximum number of messages to keep in the context.
            max_tokens: Maximum number of tokens to keep in the context.

        Returns:
            None
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens

    def add_to_agent(self, agent: ConversableAgent):
        """
        Adds a particular capability to the given agent. Must be implemented by the capability subclass.
        An implementation will typically call agent.register_hook() one or more times. See teachability.py as an example.
        """
        agent.register_hook(hookable_method=agent.process_all_messages, hook=self.truncate_messages)

    def truncate_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Truncate the messages to the maximum number of messages and tokens.

        Args:
            messages: List of messages to process.

        Returns:
            List of messages with the first system message and the last max_messages messages.
        """
        processed_messages = []
        rest_messages = messages
        processed_messages_tokens = 0

        # check if the first message is a system message and append it to the processed messages
        if len(messages) > 0:
            if messages[0]["role"] == "system":
                msg = messages[0]
                processed_messages.append(msg)
                processed_messages_tokens += token_count_utils.count_token(msg["content"])
                rest_messages = messages[1:]

        # iterate through rest of the messages and append them to the processed messages
        for msg in rest_messages[-self.max_messages :]:
            msg_tokens = token_count_utils.count_token(msg["content"])
            if processed_messages_tokens + msg_tokens > self.max_tokens:
                break
            processed_messages.append(msg)
            processed_messages_tokens += msg_tokens

        total_tokens = 0
        for msg in messages:
            total_tokens += token_count_utils.count_token(msg["content"])

        num_truncated = len(messages) - len(processed_messages)
        if num_truncated > 0 or total_tokens > processed_messages_tokens:
            print(colored(f"Truncated {len(messages) - len(processed_messages)} messages.", "yellow"))
            print(colored(f"Truncated {total_tokens - processed_messages_tokens} tokens.", "yellow"))
        return processed_messages
