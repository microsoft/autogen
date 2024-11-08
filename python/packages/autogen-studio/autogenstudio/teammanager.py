from typing import AsyncGenerator, Union, Optional
import time
from .database import AgentFactory
from .datamodel import TeamConfig, TeamResult,  TaskResult
from autogen_agentchat.messages import InnerMessage, ChatMessage
from autogen_core.base import CancellationToken


class TeamManager:
    def __init__(self) -> None:
        self.agent_factory = AgentFactory()

    async def run_stream(
        self,
        task: str,
        team_config: TeamConfig | dict,
        cancellation_token: Optional[CancellationToken] = None
    ) -> AsyncGenerator[Union[InnerMessage, ChatMessage, TaskResult], None]:
        """Stream the team's execution results"""
        start_time = time.time()

        if isinstance(team_config, dict):
            team_config = TeamConfig(**team_config)

        try:
            team = self.agent_factory.load_team(team_config)
            stream = team.run_stream(
                task=task,
                cancellation_token=cancellation_token
            )

            async for message in stream:
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                # If it's the final TaskResult, wrap it in TeamResult
                if isinstance(message, TaskResult):
                    yield TeamResult(
                        task_result=message,
                        usage="",  # Update with actual usage if available
                        duration=time.time() - start_time
                    )
                else:
                    yield message

        except Exception as e:
            # Let caller handle the exception
            raise e

    async def run(
        self,
        task: str,
        team_config: TeamConfig | dict,
        cancellation_token: Optional[CancellationToken] = None
    ) -> TeamResult:
        """Original non-streaming run method with optional cancellation"""
        start_time = time.time()
        if isinstance(team_config, dict):
            team_config = TeamConfig(**team_config)

        team = self.agent_factory.load_team(team_config)
        result = await team.run(
            task=task,
            cancellation_token=cancellation_token
        )

        return TeamResult(
            task_result=result,
            usage="",
            duration=time.time() - start_time
        )
