import json
import logging
import sys
from datetime import datetime

from pydantic import BaseModel


class FileLogHandler(logging.Handler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.file_handler = logging.FileHandler(filename)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, BaseModel):
            record.msg = json.dumps(
                {
                    "timestamp": ts,
                    "message": record.msg.model_dump(),
                    "type": record.msg.__class__.__name__,
                },
            )
        self.file_handler.emit(record)


class ConsoleLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, BaseModel):
            record.msg = json.dumps(
                {
                    "timestamp": ts,
                    "message": record.msg.model_dump_json(indent=2),
                    "type": record.msg.__class__.__name__,
                },
            )
        sys.stdout.write(f"{record.msg}\n")
