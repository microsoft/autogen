from autogen_core import Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.agents import BaseChatAgent

from ._task_runner_tool import TaskRunnerTool


class AgentToolConfig(BaseModel):
    """Configuration for the AgentTool."""

    agent: ComponentModel


class AgentTool(TaskRunnerTool, Component[AgentToolConfig]):
    """Tool that can be used to run a task using an agent.

    The tool returns the result of the task execution as a :class:`~autogen_agentchat.base.TaskResult` object.

    Args:
        agent (BaseChatAgent): The agent to be used for running the task.

    Example:

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.tools import AgentTool
            from autogen_agentchat.ui import Console
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4")
                writer = AssistantAgent(
                    name="writer",
                    description="A writer agent for generating text.",
                    model_client=model_client,
                    system_message="Write well.",
                )
                writer_tool = AgentTool(agent=writer)
                assistant = AssistantAgent(
                    name="assistant",
                    model_client=model_client,
                    tools=[writer_tool],
                    system_message="You are a helpful assistant.",
                )
                await Console(assistant.run_stream(task="Write a poem about the sea."))


            asyncio.run(main())
    """

    component_config_schema = AgentToolConfig
    component_provider_override = "autogen_agentchat.tools.AgentTool"

    def __init__(self, agent: BaseChatAgent) -> None:
        self._agent = agent
        super().__init__(agent, agent.name, agent.description)

    def _to_config(self) -> AgentToolConfig:
        return AgentToolConfig(
            agent=self._agent.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: AgentToolConfig) -> Self:
        return cls(BaseChatAgent.load_component(config.agent))
