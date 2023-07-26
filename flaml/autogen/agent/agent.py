from typing import Dict, List, Union


class Agent:
    """(Experimental) An abstract class for AI agent.

    An agent can communicate with other agents and perform actions.
    Different agents can differ in what actions they perform in the `receive` method.
    """

    def __init__(
        self,
        name: str,
    ):
        """
        Args:
            name (str): name of the agent.
        """
        # a dictionary of conversations, default value is list
        self._name = name

    @property
    def name(self):
        """Get the name of the agent."""
        return self._name

    def send(self, message: Union[Dict, str], recipient: "Agent"):
        """(Aabstract method) Send a message to another agent."""

    def receive(self, message: Union[Dict, str], sender: "Agent"):
        """(Abstract method) Receive a message from another agent."""

    def reset(self):
        """(Abstract method) Reset the agent."""

    def generate_reply(self, messages: List[Dict], default_reply: Union[str, Dict] = "") -> Union[str, Dict]:
        """(Abstract method) Generate a reply based on the received messages.

        Args:
            messages (list[dict]): a list of messages received.
            default_reply (str or dict): the default reply if no other reply is generated.
        Returns:
            str or dict: the generated reply.
        """
