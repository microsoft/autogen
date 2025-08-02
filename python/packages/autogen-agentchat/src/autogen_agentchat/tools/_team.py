from autogen_core import Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.teams import BaseGroupChat

from ._task_runner_tool import TaskRunnerTool


class TeamToolConfig(BaseModel):
    """Configuration for the TeamTool."""

    name: str
    """The name of the tool."""
    description: str
    """The name and description of the tool."""
    team: ComponentModel
    """The team to be used for running the task."""
    return_value_as_last_message: bool = False
    """Whether to return the value as the last message of the task result."""


class TeamTool(TaskRunnerTool, Component[TeamToolConfig]):
    """Tool that can be used to run a task.

    The tool returns the result of the task execution as a :class:`~autogen_agentchat.base.TaskResult` object.

    .. important::
        When using TeamTool, you **must** disable parallel tool calls in the model client configuration
        to avoid concurrency issues. Teams cannot run concurrently as they maintain internal state
        that would conflict with parallel execution. For example, set ``parallel_tool_calls=False``
        for :class:`~autogen_ext.models.openai.OpenAIChatCompletionClient` and
        :class:`~autogen_ext.models.openai.AzureOpenAIChatCompletionClient`.

    Args:
        team (BaseGroupChat): The team to be used for running the task.
        name (str): The name of the tool.
        description (str): The description of the tool.
        return_value_as_last_message (bool): Whether to use the last message content of the task result
            as the return value of the tool in :meth:`~autogen_agentchat.tools.TaskRunnerTool.return_value_as_string`.
            If set to True, the last message content will be returned as a string.
            If set to False, the tool will return all messages in the task result as a string concatenated together,
            with each message prefixed by its source (e.g., "writer: ...", "assistant: ...").

    Example:

        .. code-block:: python

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import SourceMatchTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.tools import TeamTool
            from autogen_agentchat.ui import Console
            from autogen_ext.models.ollama import OllamaChatCompletionClient


            async def main() -> None:
                # Disable parallel tool calls when using TeamTool
                model_client = OllamaChatCompletionClient(model="llama3.2")

                writer = AssistantAgent(name="writer", model_client=model_client, system_message="You are a helpful assistant.")
                reviewer = AssistantAgent(
                    name="reviewer", model_client=model_client, system_message="You are a critical reviewer."
                )
                summarizer = AssistantAgent(
                    name="summarizer",
                    model_client=model_client,
                    system_message="You combine the review and produce a revised response.",
                )
                team = RoundRobinGroupChat(
                    [writer, reviewer, summarizer], termination_condition=SourceMatchTermination(sources=["summarizer"])
                )

                # Create a TeamTool that uses the team to run tasks, returning the last message as the result.
                tool = TeamTool(
                    team=team,
                    name="writing_team",
                    description="A tool for writing tasks.",
                    return_value_as_last_message=True,
                )

                # Create model client with parallel tool calls disabled for the main agent
                main_model_client = OllamaChatCompletionClient(model="llama3.2", parallel_tool_calls=False)
                main_agent = AssistantAgent(
                    name="main_agent",
                    model_client=main_model_client,
                    system_message="You are a helpful assistant that can use the writing tool.",
                    tools=[tool],
                )
                # For handling each events manually.
                # async for message in main_agent.run_stream(
                #     task="Write a short story about a robot learning to love.",
                # ):
                #     print(message)
                # Use Console to display the messages in a more readable format.
                await Console(
                    main_agent.run_stream(
                        task="Write a short story about a robot learning to love.",
                    )
                )


            if __name__ == "__main__":
                import asyncio

                asyncio.run(main())
    """

    component_config_schema = TeamToolConfig
    component_provider_override = "autogen_agentchat.tools.TeamTool"

    def __init__(
        self, team: BaseGroupChat, name: str, description: str, return_value_as_last_message: bool = False
    ) -> None:
        self._team = team
        super().__init__(team, name, description, return_value_as_last_message=return_value_as_last_message)

    def _to_config(self) -> TeamToolConfig:
        return TeamToolConfig(
            name=self._name,
            description=self._description,
            team=self._team.dump_component(),
            return_value_as_last_message=self._return_value_as_last_message,
        )

    @classmethod
    def _from_config(cls, config: TeamToolConfig) -> Self:
        return cls(
            BaseGroupChat.load_component(config.team),
            config.name,
            config.description,
            config.return_value_as_last_message,
        )
