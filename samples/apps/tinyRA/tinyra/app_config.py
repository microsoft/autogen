import os
from pathlib import Path

from typing import Dict, Optional, Protocol
from .database.database import DatabaseManager
from .files import FileManager
from .agents.agents import AgentManager
from .llm import ChatCompletionService


class TinyRAConfiguration(Protocol):

    def initialize(self) -> None:
        pass

    def get_app_path(self) -> Path:
        pass

    def reset() -> None:
        pass


class AppConfiguration:

    DEFAULT_APP_PATH: Path = Path.home() / ".tinyra"

    def __init__(
        self,
        app_path: Optional[Path],
        db_manager: DatabaseManager,
        file_manager: FileManager,
        agent_manager: AgentManager,
        llm_service: ChatCompletionService,
    ):
        self._app_path = app_path or self.DEFAULT_APP_PATH
        if not isinstance(db_manager, DatabaseManager):
            raise ValueError("db_manager must be an instance of DatabaseManager")
        self.db_manager = db_manager
        self.file_manager = file_manager
        self.agent_manager = agent_manager
        self.llm_service = llm_service

    async def initialize(self):
        """Initialize the app configuration."""
        # create the data path if it does not exist
        os.makedirs(self._app_path, exist_ok=True)

        # initialize the database
        await self.db_manager.initialize()

    def get_app_path(self):
        if not self._app_path.exists():
            raise FileNotFoundError(f"Data path {self._app_path} does not exist!")
        return self._app_path
