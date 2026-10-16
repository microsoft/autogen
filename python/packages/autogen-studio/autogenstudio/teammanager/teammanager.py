import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Sequence, Union

import aiofiles
import yaml
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import BaseGroupChat
from autogen_core import EVENT_LOGGER_NAME, CancellationToken, ComponentModel
from autogen_core.logging import LLMCallEvent

from ..datamodel.types import EnvironmentVariable, LLMCallEventMessage, RedactionConfig, TeamResult
from ..utils.redactor import SensitiveDataRedactor
from ..web.managers.run_context import RunContext

logger = logging.getLogger(__name__)

SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]


class RunEventLogger(logging.Handler):
    """Event logger that queues LLMCallEvents for streaming"""

    def __init__(self):
        super().__init__()
        self.events: asyncio.Queue[LLMCallEventMessage] = asyncio.Queue()

    def emit(self, record: logging.LogRecord):
        if isinstance(record.msg, LLMCallEvent):
            self.events.put_nowait(LLMCallEventMessage(content=str(record.msg)))


class TeamManager:
    """Manages team operations including loading configs and running teams"""

    def __init__(self):
        self._team: Optional[BaseGroupChat] = None
        self._run_context = RunContext()

    @staticmethod
    async def load_from_file(path: Union[str, Path]) -> Any:
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
    async def load_from_directory(directory: Union[str, Path]) -> List[Any]:
        """Load all team configurations from a directory"""
        directory = Path(directory)
        configs: List[Any] = []
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
        self,
        team_config: Union[str, Path, Dict[str, Any], ComponentModel],
        input_func: Optional[InputFuncType] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
    ) -> BaseGroupChat:
        """Create team instance from config"""
        if isinstance(team_config, (str, Path)):
            config = await self.load_from_file(team_config)
        elif isinstance(team_config, dict):
            config = team_config
        elif isinstance(team_config, ComponentModel):
            config = team_config.model_dump()
        else:
            raise ValueError(f"Unsupported team_config type: {type(team_config)}")

        # Load env vars into environment if provided
        if env_vars:
            logger.info("Loading environment variables")
            for var in env_vars:
                os.environ[var.name] = var.value

        self._team = BaseGroupChat.load_component(config)

        for agent in self._team._participants:  # type: ignore
            if hasattr(agent, "input_func") and isinstance(agent, UserProxyAgent) and input_func:
                agent.input_func = input_func

        return self._team

    async def run_stream(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None,
        team_config: Union[str, Path, Dict[str, Any], ComponentModel],
        input_func: Optional[InputFuncType] = None,
        cancellation_token: Optional[CancellationToken] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
        redaction_config: Optional[RedactionConfig] = None,
    ) -> AsyncGenerator[Union[BaseAgentEvent | BaseChatMessage | LLMCallEvent, BaseChatMessage, TeamResult], None]:
        """Stream team execution results"""
        start_time = time.time()
        team = None
        redactor = SensitiveDataRedactor(config=redaction_config, env_vars=env_vars) if redaction_config else None

        # Setup logger correctly
        logger = logging.getLogger(EVENT_LOGGER_NAME)
        logger.setLevel(logging.INFO)
        llm_event_logger = RunEventLogger()
        logger.handlers = [llm_event_logger]  # Replace all handlers

        try:
            team = await self._create_team(team_config, input_func, env_vars)

            async for message in team.run_stream(task=task, cancellation_token=cancellation_token):
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                if isinstance(message, TaskResult):
                    tr = TeamResult(task_result=message, usage="", duration=time.time() - start_time)
                    yield redactor.redact_message(tr) if redactor else tr
                else:
                    yield redactor.redact_message(message) if redactor else message

                # Check for any LLM events
                while not llm_event_logger.events.empty():
                    event = await llm_event_logger.events.get()
                    yield redactor.redact_message(event) if redactor else event
        finally:
            # Cleanup - remove our handler
            if llm_event_logger in logger.handlers:
                logger.handlers.remove(llm_event_logger)

            # Ensure cleanup happens
            if team and hasattr(team, "_participants"):
                for agent in team._participants:  # type: ignore
                    if hasattr(agent, "close"):
                        await agent.close()

    async def run(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None,
        team_config: Union[str, Path, Dict[str, Any], ComponentModel],
        input_func: Optional[InputFuncType] = None,
        cancellation_token: Optional[CancellationToken] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
        redaction_config: Optional[RedactionConfig] = None,
    ) -> TeamResult:
        """Run team synchronously"""
        start_time = time.time()
        team = None
        redactor = SensitiveDataRedactor(config=redaction_config, env_vars=env_vars) if redaction_config else None

        try:
            team = await self._create_team(team_config, input_func, env_vars)
            result = await team.run(task=task, cancellation_token=cancellation_token)

            tr = TeamResult(task_result=result, usage="", duration=time.time() - start_time)
            return redactor.redact_message(tr) if redactor else tr

        finally:
            if team and hasattr(team, "_participants"):
                for agent in team._participants:  # type: ignore
                    if hasattr(agent, "close"):
                        await agent.close()
