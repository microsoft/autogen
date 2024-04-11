from typing import Any, Dict, Optional

from autogen.logger.base_logger import BaseLogger
from autogen.logger.sqlite_logger import SqliteLogger
from autogen.logger.cosmos_db_logger import CosmosDBLogger

__all__ = ("LoggerFactory",)

try:
    from autogen.logger.cosmos_db_logger import CosmosDBLogger
    cosmos_imported = True
except ImportError:
    cosmos_imported = False

class LoggerFactory:
    @staticmethod
    def get_logger(logger_type: str = "sqlite", config: Optional[Dict[str, Any]] = None) -> BaseLogger:
        if config is None:
            config = {}

        if logger_type == "sqlite":
            return SqliteLogger(config)
        elif logger_type == "cosmos":
            if cosmos_imported:
                return CosmosDBLogger(config)
            else:
                raise ImportError("CosmosDBLogger could not be imported. Please ensure the cosmos package is installed.")
        else:
            raise ValueError(f"[logger_factory] Unknown logger type: {logger_type}")
