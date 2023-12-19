from autogen.agentchat.assistant_agent import ConversableAgent


class AgentCapability:
    """Base class for composable capabilities that can be added to an agent."""

    def __init__(self):
        pass

    def add_to_agent(self, agent: ConversableAgent):
        """
        Adds a particular capability to the given agent. Must be implemented by the capability subclass.
        An implementation will typically call agent.register_hook() one or more times. See teachability.py as an example.
        """
        raise NotImplementedError
