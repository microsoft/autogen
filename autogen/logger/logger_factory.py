from typing import Any, Dict, Optional

from autogen.logger.base_logger import BaseLogger
from autogen.logger.sqlite_logger import SqliteLogger
from autogen.logger.cosmos_db_logger import CosmosDBLogger

__all__ = ("LoggerFactory",)


class LoggerFactory:
    @staticmethod
    def get_logger(logger_type: str = "sqlite", config: Optional[Dict[str, Any]] = None) -> BaseLogger:
        if config is None:
            config = {}

        if logger_type == "sqlite":
            return SqliteLogger(config)
        elif logger_type == "cosmos":
            return CosmosDBLogger(config)
        else:
            raise ValueError(f"[logger_factory] Unknown logger type: {logger_type}")
