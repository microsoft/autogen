from typing import Optional

from autogen_core.models import ModelCapabilities, ModelInfo
from pydantic import BaseModel


class GeminiClientConfigurationConfigModel(BaseModel):
    model: str
    api_key: Optional[str] = None
    vertexai: Optional[bool] = None
    project: Optional[str] = None
    location: Optional[str] = None
    timeout: Optional[float] = None
    max_retries: Optional[int] = None

    # You can use either model_capabilities (deprecated) or model_info
    model_capabilities: Optional[ModelCapabilities] = None
    model_info: Optional[ModelInfo] = None

    # If needed for custom headers or other advanced usage:
    default_headers: dict[str, str] | None = None
