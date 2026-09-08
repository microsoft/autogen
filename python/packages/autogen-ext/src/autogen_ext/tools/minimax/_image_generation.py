from __future__ import annotations

import asyncio
from typing import Any, Literal, Mapping

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field, SecretStr, model_validator
from typing_extensions import Self

MiniMaxImageModel = Literal["image-01", "image-01-live"]
MiniMaxRegion = Literal["global_en", "cn_zh"]
ImageResponseFormat = Literal["url", "base64"]

_REGIONAL_ENDPOINTS: Mapping[MiniMaxRegion, str] = {
    "global_en": "https://api.minimax.io/v1/image_generation",
    "cn_zh": "https://api.minimaxi.com/v1/image_generation",
}


class MiniMaxImageGenerationArgs(BaseModel):
    """Arguments accepted by the MiniMax image generation tool."""

    prompt: str = Field(min_length=1, max_length=1500, description="A text description of the image to generate")
    aspect_ratio: Literal["1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9"] | None = Field(
        default=None, description="The output image aspect ratio"
    )
    width: int | None = Field(default=None, ge=512, le=2048, description="The output image width in pixels")
    height: int | None = Field(default=None, ge=512, le=2048, description="The output image height in pixels")
    response_format: ImageResponseFormat = Field(default="url", description="Return image URLs or base64 data")
    seed: int | None = Field(default=None, description="A seed used to make generation reproducible")
    n: int = Field(default=1, ge=1, le=9, description="The number of images to generate")
    prompt_optimizer: bool = Field(default=False, description="Whether to optimize the prompt before generation")

    @model_validator(mode="after")
    def validate_dimensions(self) -> Self:
        if (self.width is None) != (self.height is None):
            raise ValueError("width and height must be provided together")
        if self.width is not None and self.height is not None and (self.width % 8 != 0 or self.height % 8 != 0):
            raise ValueError("width and height must be divisible by 8")
        return self


class MiniMaxImageGenerationResult(BaseModel):
    """Images and request metadata returned by the image generation endpoint."""

    images: list[str]
    response_format: ImageResponseFormat
    success_count: int
    failed_count: int


class MiniMaxImageGenerationToolConfig(BaseModel):
    """Serializable configuration for :class:`MiniMaxImageGenerationTool`."""

    api_key: SecretStr
    model: MiniMaxImageModel = "image-01"
    region: MiniMaxRegion = "global_en"
    timeout: float = Field(default=60.0, gt=0)


class MiniMaxImageGenerationTool(
    BaseTool[MiniMaxImageGenerationArgs, MiniMaxImageGenerationResult], Component[MiniMaxImageGenerationToolConfig]
):
    """Generate images with MiniMax and return URL or base64 results.

    Args:
        api_key: API key sent with Bearer authentication.
        model: Image generation model to use.
        region: Regional API endpoint to call.
        timeout: Request timeout in seconds.

    .. note::
        Install the ``http-tool`` extra before using this tool:
        ``pip install \"autogen-ext[http-tool]\"``.
    """

    component_config_schema = MiniMaxImageGenerationToolConfig
    component_provider_override = "autogen_ext.tools.minimax.MiniMaxImageGenerationTool"

    def __init__(
        self,
        api_key: str,
        model: MiniMaxImageModel = "image-01",
        region: MiniMaxRegion = "global_en",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            MiniMaxImageGenerationArgs,
            MiniMaxImageGenerationResult,
            "minimax_image_generation",
            "Generate images from a text prompt with MiniMax.",
        )
        self._config = MiniMaxImageGenerationToolConfig(
            api_key=SecretStr(api_key), model=model, region=region, timeout=timeout
        )

    async def run(
        self, args: MiniMaxImageGenerationArgs, cancellation_token: CancellationToken
    ) -> MiniMaxImageGenerationResult:
        payload: dict[str, Any] = {
            "model": self._config.model,
            **args.model_dump(exclude_none=True),
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            request = asyncio.ensure_future(
                client.post(_REGIONAL_ENDPOINTS[self._config.region], headers=headers, json=payload)
            )
            response = await cancellation_token.link_future(request)

        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("MiniMax image generation returned an invalid response")

        base_response = body.get("base_resp")
        if not isinstance(base_response, dict):
            raise ValueError("MiniMax image generation response is missing base_resp")
        status_code = base_response.get("status_code")
        if status_code != 0:
            status_message = base_response.get("status_msg") or "unknown error"
            raise RuntimeError(f"MiniMax image generation failed ({status_code}): {status_message}")

        data = body.get("data")
        if not isinstance(data, dict):
            raise ValueError("MiniMax image generation response is missing image data")
        result_key = "image_urls" if args.response_format == "url" else "image_base64"
        raw_images = data.get(result_key)
        if not isinstance(raw_images, list) or not all(isinstance(image, str) and image for image in raw_images):
            raise ValueError(f"MiniMax image generation response is missing {result_key}")

        metadata = body.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        success_count = metadata.get("success_count", len(raw_images))
        failed_count = metadata.get("failed_count", 0)
        try:
            parsed_success_count = int(success_count)
            parsed_failed_count = int(failed_count)
        except (TypeError, ValueError) as exc:
            raise ValueError("MiniMax image generation response contains invalid metadata") from exc

        return MiniMaxImageGenerationResult(
            images=raw_images,
            response_format=args.response_format,
            success_count=parsed_success_count,
            failed_count=parsed_failed_count,
        )

    def _to_config(self) -> MiniMaxImageGenerationToolConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: MiniMaxImageGenerationToolConfig) -> Self:
        return cls(
            api_key=config.api_key.get_secret_value(),
            model=config.model,
            region=config.region,
            timeout=config.timeout,
        )
