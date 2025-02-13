from typing import Dict, List, Literal, Optional, Union

from autogen_core.models import ModelInfo
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ResponseFormatConfig(BaseModel):
    type: Literal["text", "json_object"] = Field(
        default="text",
        description="The format of the model's response."
    )


class GeminiClientArgumentsConfig(BaseModel):
    model: str = Field(
        ...,
        description="The name of the model to use."
    )
    timeout: Optional[float] = Field(
        default=None,
        description="The timeout for the API request."
    )
    max_retries: int = Field(
        default=3,
        description="The maximum number of retries for the API request."
    )
    model_info: Optional[ModelInfo] = Field(
        default=None,
        description="Information about the model."
    )
    default_headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Default headers to include in the API request."
    )


class GeminiCreateArguments(BaseModel):
    temperature: Optional[float] = Field(
        default=None,
        description="The temperature for the model. Must be between 0 and 1."
    )
    top_p: Optional[float] = Field(
        default=None,
        description="The top_p value for the model. Must be between 0 and 1."
    )
    top_k: Optional[int] = Field(
        default=None,
        description="The top_k value for the model."
    )
    max_output_tokens: Optional[int] = Field(
        default=None,
        description="The maximum number of tokens to generate."
    )
    stop_sequences: Optional[List[str]] = Field(
        default=None,
        description="A list of stop sequences."
    )
    candidate_count: Optional[int] = Field(
        default=None,
        description="The number of candidates to generate."
    )
    safety_settings: Optional[Dict[str, Dict[str, str]]] = Field(
        default=None,
        description="The safety settings for the model."
    )
    response_format: Optional[ResponseFormatConfig] = Field(
        default=None,
        description="The format of the model's response."
    )


class GeminiClientConfig(GeminiClientArgumentsConfig, GeminiCreateArguments):
    api_key: str = Field(
        ...,
        description="The API key to use."
    )
    base_url: Optional[str] = Field(
        default=None,
        description="The base URL for the API. Not used by the google-genai library, but kept for consistency."
    )


class VertexAIClientConfig(GeminiClientArgumentsConfig, GeminiCreateArguments):
    project_id: str = Field(
        ...,
        description="The project ID to use."
    )
    location: str = Field(
        default="us-central1",
        description="The location to use."
    )
    credentials_path: Optional[str] = Field(
        default=None,
        description="The path to the credentials file. Could also use ADC."
    )
