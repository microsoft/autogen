from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str
    # Framework-generated identifier for correlating the call with its result.
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
