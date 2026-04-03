"""Configuration for MnemoPay tools."""

from typing import Optional

from pydantic import BaseModel, Field


class MnemoPayConfig(BaseModel):
    """Configuration for connecting to the MnemoPay MCP server.

    Attributes:
        agent_id: Unique identifier for this agent. Defaults to ``"autogen-agent"``.
        mode: Operation mode — ``"quick"`` (in-memory) or ``"full"`` (persistent).
        server_url: Optional HTTP URL for a remote MnemoPay server. When set,
            tools call the server over HTTP instead of spawning a local stdio process.
        npx_command: The npx binary name. Use ``"npx.cmd"`` on Windows.
    """

    agent_id: str = Field(default="autogen-agent", description="Unique identifier for this agent.")
    mode: str = Field(default="quick", description="Operation mode: 'quick' (in-memory) or 'full' (persistent).")
    server_url: Optional[str] = Field(
        default=None, description="HTTP URL for a remote MnemoPay server. If None, spawns a local stdio process."
    )
    npx_command: str = Field(
        default="npx", description="The npx binary name. Use 'npx.cmd' on Windows."
    )
