from collections import defaultdict


class Agent:
    """An abstract class for AI agent.
    An agent can communicate with other agents, human and perform actions.
    Different agents can differ in how and who they communicate with, and what actions they can perform. For example, an autonomous agent can communicate with human and other agents, and perform actions by creating agents and sending messages to other agents. A planning agent can communicate with other agents to make a plan and keep track of tasks. An execution agent can only communicate with other agents, and perform actions such as executing a command or code.
    """

    def __init__(self, name, system_message=""):
        # empty memory
        self._memory = []
        # a dictionary of conversations, default value is list
        self._conversations = defaultdict(list)
        self._name = name
        self._system_message = system_message

    @property
    def name(self):
        """Get the name of the agent."""
        return self._name

    def _remember(self, memory):
        """Remember something."""
        self._memory.append(memory)

    def _send(self, message, recipient):
        """Send a message to another agent."""
        self._conversations[recipient.name].append({"content": message, "role": "assistant"})
        recipient.receive(message, self)

    def _receive(self, message, sender):
        """Receive a message from another agent."""
        # print(self.name, "received message from", sender.name, ":", message)
        self._conversations[sender.name].append({"content": message, "role": "user"})

    def receive(self, message, sender):
        """Receive a message from another agent.
        This method is called by the sender.
        It needs to be overriden by the subclass to perform followup actions.
        """
        self._receive(message, sender)
        # perform actions based on the message
