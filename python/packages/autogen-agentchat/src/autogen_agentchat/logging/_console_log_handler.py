import json
import logging
import sys
from datetime import datetime

from pydantic import BaseModel


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
