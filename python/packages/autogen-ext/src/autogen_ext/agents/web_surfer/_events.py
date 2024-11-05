from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class WebSurferEvent:
    source: str
    message: str
    url: str
    action: str | None = None
    arguments: Dict[str, Any] | None = None
