from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryScope(str, Enum):
    AGENT = "agent"
    GROUP = "group"
    GLOBAL = "global"


class WritePolicyEntry(BaseModel):
    allowed_agents: List[str] = Field(default_factory=lambda: ["*"])


class SharedMemoryConfig(BaseModel):
    db_path: str = Field(
        default=":memory:",
        description="Path to SQLite database file. Use ':memory:' for in-memory store.",
    )
    default_top_k: int = Field(default=5, ge=1, le=50)
    max_capsule_bytes: int = Field(
        default=2048,
        description="Maximum size in bytes for a single recall capsule.",
    )
    write_policies: Dict[str, WritePolicyEntry] = Field(
        default_factory=lambda: {
            "agent": WritePolicyEntry(allowed_agents=["*"]),
            "group": WritePolicyEntry(allowed_agents=["*"]),
            "global": WritePolicyEntry(allowed_agents=[]),
        },
        description="Per-scope write authorization. Empty list = no one can write; ['*'] = open.",
    )
    group_id: Optional[str] = Field(
        default=None,
        description="Group identifier for group-scoped facts. Required when using group scope.",
    )
