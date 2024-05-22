from typing import Any, Dict, Literal, Optional

from autogen.logger.base_logger import BaseLogger
from autogen.logger.file_logger import FileLogger
from autogen.logger.sqlite_logger import SqliteLogger

try:
    from autogen.logger.cosmos_db_logger import CosmosDBLogger, CosmosDBLoggerConfig

    cosmos_imported = True
except ImportError:
    cosmos_imported = False

__all__ = ("LoggerFactory",)


class LoggerFactory:
    @staticmethod
    def get_logger(
        logger_type: Literal["sqlite", "file"] = "sqlite", config: Optional[Dict[str, Any]] = None
    ) -> BaseLogger:
        if config is None:
            config = {}

        if logger_type == "sqlite":
            return SqliteLogger(config)
        elif logger_type == "file":
            return FileLogger(config)
        elif logger_type == "cosmos":
            if not cosmos_imported:
                raise ImportError(
                    "CosmosDBLogger and CosmosDBLoggerConfig could not be imported. Please ensure the cosmos package is installed by using pip install pyautogen[cosmosdb]."
                )
            # Validate configuration for CosmosDBLogger
            required_keys = {"connection_string", "database_id", "container_id"}
            if isinstance(config, dict) and required_keys.issubset(config.keys()):
                cosmos_config: CosmosDBLoggerConfig = {
                    "connection_string": config["connection_string"],
                    "database_id": config["database_id"],
                    "container_id": config["container_id"],
                }
                return CosmosDBLogger(cosmos_config)  # Config validated and passed as CosmosDBLoggerConfig
            else:
                raise ValueError(
                    "Provided configuration is missing required keys or is not properly formatted for CosmosDBLogger."
                )
        else:
            raise ValueError(f"[logger_factory] Unknown logger type: {logger_type}")
