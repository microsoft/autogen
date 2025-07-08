from autogen_core import Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.agents import BaseChatAgent

from ._task_runner_tool import TaskRunnerTool


class AgentToolConfig(BaseModel):
    """Configuration for the AgentTool."""

    agent: ComponentModel
    """The agent to be used for running the task."""

    return_value_as_last_message: bool = False
    """Whether to return the value as the last message of the task result."""


class AgentTool(TaskRunnerTool, Component[AgentToolConfig]):
    """Tool that can be used to run a task using an agent.

    The tool returns the result of the task execution as a :class:`~autogen_agentchat.base.TaskResult` object.

    Args:
        agent (BaseChatAgent): The agent to be used for running the task.
        return_value_as_last_message (bool): Whether to use the last message content of the task result
            as the return value of the tool in :meth:`~autogen_agentchat.tools.TaskRunnerTool.return_value_as_string`.
            If set to True, the last message content will be returned as a string.
            If set to False, the tool will return all messages in the task result as a string concatenated together,
            with each message prefixed by its source (e.g., "writer: ...", "assistant: ...").

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

    def __init__(self, agent: BaseChatAgent, return_value_as_last_message: bool = False) -> None:
        self._agent = agent
        super().__init__(
            agent, agent.name, agent.description, return_value_as_last_message=return_value_as_last_message
        )

    def _to_config(self) -> AgentToolConfig:
        return AgentToolConfig(
            agent=self._agent.dump_component(),
            return_value_as_last_message=self._return_value_as_last_message,
        )

    @classmethod
    def _from_config(cls, config: AgentToolConfig) -> Self:
        return cls(BaseChatAgent.load_component(config.agent), config.return_value_as_last_message)
