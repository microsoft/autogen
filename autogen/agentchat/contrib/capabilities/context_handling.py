from typing import Dict, Optional, Union, List, Tuple, Any
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen import ConversableAgent


class LongContextCapability:
    """Base class for composable capabilities that can be added to an agent.

    Note about this capability:
        - this does not modify the agents chat history permanently
        - the processing happen every invocation
    """

    def __init__(self, max_messages=2):
        self.max_messages = max_messages

    def add_to_agent(self, agent: ConversableAgent):
        """
        Adds a particular capability to the given agent. Must be implemented by the capability subclass.
        An implementation will typically call agent.register_hook() one or more times. See teachability.py as an example.
        """
        agent.register_hook(hookable_method=agent.process_all_messages, hook=self.truncate_messages)

    def truncate_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Truncates the message history to the last n messages *excluding* the system message.
        System messages are not truncated.

        Args:
            messages: List of messages to be truncated.

        Returns:
            List of messages truncated to the last n messages.
        """
        processed_messages = []
        if len(messages) > self.max_messages:
            if messages[0]["role"] == "system":
                processed_messages.append(messages[0])
        for message in reversed(messages):
            if len(processed_messages) >= self.max_messages:
                break
            processed_messages.append(message)
        num_truncated = len(messages) - len(processed_messages)
        if num_truncated > 0:
            print(f"Truncated {len(messages) - len(processed_messages)} messages.")
        return processed_messages
