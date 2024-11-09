from typing import AsyncGenerator, Union, Optional
import time
from .database import ComponentFactory
from .datamodel import TeamResult, TaskResult, ComponentConfigInput
from autogen_agentchat.messages import InnerMessage, ChatMessage
from autogen_core.base import CancellationToken


class TeamManager:
    def __init__(self) -> None:
        self.component_factory = ComponentFactory()

    async def run_stream(
        self,
        task: str,
        team_config: ComponentConfigInput,
        cancellation_token: Optional[CancellationToken] = None
    ) -> AsyncGenerator[Union[InnerMessage, ChatMessage, TaskResult], None]:
        """Stream the team's execution results"""
        start_time = time.time()

        try:
            # Let factory handle all config processing
            team = await self.component_factory.load(team_config)

            stream = team.run_stream(
                task=task,
                cancellation_token=cancellation_token
            )

            async for message in stream:
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                if isinstance(message, TaskResult):
                    yield TeamResult(
                        task_result=message,
                        usage="",
                        duration=time.time() - start_time
                    )
                else:
                    yield message

        except Exception as e:
            raise e

    async def run(
        self,
        task: str,
        team_config: ComponentConfigInput,
        cancellation_token: Optional[CancellationToken] = None
    ) -> TeamResult:
        """Original non-streaming run method with optional cancellation"""
        start_time = time.time()

        # Let factory handle all config processing
        team = await self.component_factory.load(team_config)
        result = await team.run(
            task=task,
            cancellation_token=cancellation_token
        )

        return TeamResult(
            task_result=result,
            usage="",
            duration=time.time() - start_time
        )
