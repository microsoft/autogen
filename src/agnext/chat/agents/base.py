from agnext.core.agent_runtime import AgentRuntime
from agnext.core.base_agent import BaseAgent


class BaseChatAgent(BaseAgent):
    """The BaseAgent class for the chat API."""

    def __init__(self, name: str, description: str, runtime: AgentRuntime) -> None:
        super().__init__(name, runtime)
        self._description = description

    @property
    def description(self) -> str:
        """The description of the agent."""
        return self._description
