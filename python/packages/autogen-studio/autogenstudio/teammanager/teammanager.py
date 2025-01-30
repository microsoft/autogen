import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator, Callable, List, Optional, Union

import aiofiles
import yaml
from autogen_agentchat.base import TaskResult, Team
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_core import CancellationToken, Component, ComponentModel

from ..datamodel.types import TeamResult

logger = logging.getLogger(__name__)


class TeamManager:
    """Manages team operations including loading configs and running teams"""

    @staticmethod
    async def load_from_file(path: Union[str, Path]) -> dict:
        """Load team configuration from JSON/YAML file"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        async with aiofiles.open(path) as f:
            content = await f.read()
            if path.suffix == ".json":
                return json.loads(content)
            elif path.suffix in (".yml", ".yaml"):
                return yaml.safe_load(content)
            raise ValueError(f"Unsupported file format: {path.suffix}")

    @staticmethod
    async def load_from_directory(directory: Union[str, Path]) -> List[dict]:
        """Load all team configurations from a directory

        Args:
            directory (Union[str, Path]): Path to directory containing config files

        Returns:
            List[dict]: List of loaded team configurations
        """
        directory = Path(directory)
        configs = []
        valid_extensions = {".json", ".yaml", ".yml"}

        for path in directory.iterdir():
            if path.is_file() and path.suffix.lower() in valid_extensions:
                try:
                    config = await TeamManager.load_from_file(path)
                    configs.append(config)
                except Exception as e:
                    logger.error(f"Failed to load {path}: {e}")

        return configs

    async def _create_team(
        self, team_config: Union[str, Path, dict, ComponentModel], input_func: Optional[Callable] = None
    ) -> Component:
        """Create team instance from config"""
        # Handle different input types
        if isinstance(team_config, (str, Path)):
            config = await self.load_from_file(team_config)
        elif isinstance(team_config, dict):
            config = team_config
        else:
            config = team_config.model_dump()

        # Use Component.load_component directly
        team = Team.load_component(config)

        for agent in team._participants:
            if hasattr(agent, "input_func"):
                agent.input_func = input_func

        # TBD - set input function
        return team

    async def run_stream(
        self,
        task: str,
        team_config: Union[str, Path, dict, ComponentModel],
        input_func: Optional[Callable] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[AgentEvent | ChatMessage, ChatMessage, TaskResult], None]:
        """Stream team execution results"""
        start_time = time.time()
        team = None

        try:
            team = await self._create_team(team_config, input_func)

            async for message in team.run_stream(task=task, cancellation_token=cancellation_token):
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                if isinstance(message, TaskResult):
                    yield TeamResult(task_result=message, usage="", duration=time.time() - start_time)
                else:
                    yield message

        finally:
            # Ensure cleanup happens
            if team and hasattr(team, "_participants"):
                for agent in team._participants:
                    if hasattr(agent, "close"):
                        await agent.close()

    async def run(
        self,
        task: str,
        team_config: Union[str, Path, dict, ComponentModel],
        input_func: Optional[Callable] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> TeamResult:
        """Run team synchronously"""
        start_time = time.time()
        team = None

        try:
            team = await self._create_team(team_config, input_func)
            result = await team.run(task=task, cancellation_token=cancellation_token)

            return TeamResult(task_result=result, usage="", duration=time.time() - start_time)

        finally:
            # Ensure cleanup happens
            if team and hasattr(team, "_participants"):
                for agent in team._participants:
                    if hasattr(agent, "close"):
                        await agent.close()
