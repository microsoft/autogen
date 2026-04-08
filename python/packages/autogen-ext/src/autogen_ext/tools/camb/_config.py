from typing import Optional

from pydantic import BaseModel


class CambToolConfig(BaseModel):
    """Configuration for CAMB.AI tools.

    Args:
        api_key: CAMB.AI API key. If not provided, falls back to CAMB_API_KEY environment variable.
        base_url: Base URL for the CAMB.AI API.
        timeout: Request timeout in seconds.
        max_poll_attempts: Maximum number of polling attempts for async tasks.
        poll_interval: Interval between polling attempts in seconds.
    """

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: Optional[float] = None
    max_poll_attempts: int = 60
    poll_interval: float = 2.0
