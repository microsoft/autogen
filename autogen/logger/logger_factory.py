from typing import Any, Dict, Literal, Optional

from autogen.logger.base_logger import BaseLogger
from autogen.logger.file_logger import FileLogger
from autogen.logger.sqlite_logger import SqliteLogger

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
        else:
            raise ValueError(f"[logger_factory] Unknown logger type: {logger_type}")
