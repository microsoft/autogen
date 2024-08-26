# Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Portions derived from  https://github.com/microsoft/autogen are under the MIT License.
# SPDX-License-Identifier: MIT
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
