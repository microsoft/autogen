from typing import Any, Dict, List, Literal, Optional, Type, Union

import google.auth.credentials
from autogen_core.models import ModelInfo
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class ResponseFormatConfig(TypedDict, total=False):
    type: Literal["text", "json_object", "pydantic"]
    # The format of the model's response.
    schema: Optional[Union[Dict[str, Any], Type[BaseModel]]]
    # Optional schema for json_object or pydantic output types.


class GeminiChatClientArgumentsConfig(TypedDict, total=False):
    model: str
    # The name of the model to use.
    timeout: Optional[float]
    # The timeout for the API request.
    max_retries: int
    # The maximum number of retries for the API request.
    model_info: ModelInfo
    # Information about the model.
    http_options: Optional[Dict[str, Any]]
    # Optional HTTP options for the API request.


class GeminiCreateArguments(TypedDict, total=False):
    temperature: Optional[float]
    # The temperature for the model. Must be between 0 and 1.
    top_p: Optional[float]
    # The top_p value for the model. Must be between 0 and 1.
    top_k: Optional[int]
    # The top_k value for the model.
    max_output_tokens: Optional[int]
    # The maximum number of tokens to generate.
    stop_sequences: Optional[List[str]]
    # A list of stop sequences.
    candidate_count: Optional[int]
    # The number of candidates to generate.
    safety_settings: Optional[Dict[str, Dict[str, str]]]
    # Safety settings for content filtering. Keys are harm categories, values are dictionaries with 'threshold' key.
    response_format: Optional[ResponseFormatConfig]
    # The format of the model's response.


class GeminiChatClientConfig(GeminiChatClientArgumentsConfig, GeminiCreateArguments):
    api_key: str = Field(..., description="The API key to use.")


class VertexAIChatClientConfig(GeminiChatClientArgumentsConfig, GeminiCreateArguments):
    """Configuration for Vertex AI Gemini chat client."""

    project_id: str
    location: str
    credentials: Optional[google.auth.credentials.Credentials] = None
