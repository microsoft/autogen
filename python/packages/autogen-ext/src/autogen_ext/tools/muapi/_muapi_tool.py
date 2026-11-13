"""MuAPI image and video generation tools for AutoGen.

MuAPI (https://muapi.ai) provides unified access to 400+ generative media
models through a single API — Flux, Midjourney, GPT-4o, Veo3, Kling, Wan,
Runway, Sora, Suno, and more.
"""

from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any

import aiohttp

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field

BASE_URL = "https://api.muapi.ai/api/v1"


class MuApiImageInput(BaseModel):
    prompt: Annotated[str, Field(description="Text description of the image to generate.")]
    model: Annotated[
        str,
        Field(
            default="flux-schnell",
            description=(
                "Model to use. Options: flux-schnell, flux-dev, flux-kontext-pro, "
                "hidream-fast, midjourney, gpt4o, gpt-image-2, imagen4, imagen4-fast, "
                "seedream, reve, ideogram, hunyuan, wan2.1, qwen."
            ),
        ),
    ] = "flux-schnell"
    width: Annotated[int | None, Field(default=None, description="Image width in pixels.")] = None
    height: Annotated[int | None, Field(default=None, description="Image height in pixels.")] = None


class MuApiVideoInput(BaseModel):
    prompt: Annotated[str, Field(description="Text description of the video to generate.")]
    model: Annotated[
        str,
        Field(
            default="veo3-fast",
            description=(
                "Model to use. Options: veo3, veo3-fast, kling-master, wan2.1, wan2.2, "
                "seedance-pro, seedance-pro-fast, runway, pixverse, sora, hunyuan."
            ),
        ),
    ] = "veo3-fast"
    duration: Annotated[int, Field(default=5, description="Duration in seconds (3-60).")] = 5
    aspect_ratio: Annotated[
        str, Field(default="16:9", description="Aspect ratio: 16:9, 9:16, 1:1, 4:3.")
    ] = "16:9"


class MuApiImageOutput(BaseModel):
    image_url: str
    model: str
    prompt: str


class MuApiVideoOutput(BaseModel):
    video_url: str
    model: str
    prompt: str


async def _submit_and_poll(
    api_key: str,
    endpoint: str,
    payload: dict[str, Any],
    poll_interval: float = 3.0,
    timeout: float = 300.0,
) -> str:
    """Submit a muapi.ai job and async-poll until completion."""
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/{endpoint}", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        request_id: str = data["request_id"]

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(poll_interval)
            async with session.get(
                f"{BASE_URL}/predictions/{request_id}/result",
                headers={"x-api-key": api_key},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as poll_resp:
                poll_resp.raise_for_status()
                result = await poll_resp.json()

            status: str = result.get("status", "pending")
            if status == "completed":
                outputs: list[str] = result.get("outputs", [])
                if not outputs:
                    raise RuntimeError("Generation completed but returned no outputs")
                return outputs[0]
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"Generation {status}: {result.get('error', '')}")

    raise TimeoutError(f"MuAPI generation timed out after {timeout}s")


class MuApiImageTool(BaseTool[MuApiImageInput, MuApiImageOutput]):
    """Generate images using muapi.ai — a unified API for 400+ image models.

    Supports Flux, Midjourney, GPT-4o Image, Google Imagen 4, Seedream,
    HiDream, Reve, Ideogram, Hunyuan, Wan, and more.

    Args:
        api_key: muapi.ai API key. Get one at https://muapi.ai/dashboard/api-keys
        poll_interval: Seconds between status polls (default 3.0)
        timeout: Max seconds to wait for generation (default 300)
    """

    component_type = "tool"
    component_version = 1
    component_config_schema = MuApiImageInput

    def __init__(self, api_key: str, poll_interval: float = 3.0, timeout: float = 300.0) -> None:
        super().__init__(
            args_type=MuApiImageInput,
            return_type=MuApiImageOutput,
            name="muapi_generate_image",
            description=(
                "Generate an image from a text prompt using muapi.ai. "
                "Supports Flux, Midjourney, GPT-4o Image, Google Imagen 4, Seedream, and more. "
                "Returns the URL of the generated image."
            ),
        )
        self._api_key = api_key
        self._poll_interval = poll_interval
        self._timeout = timeout

    async def run(self, args: MuApiImageInput, cancellation_token: CancellationToken) -> MuApiImageOutput:
        payload: dict[str, Any] = {"prompt": args.prompt}
        if args.width:
            payload["width"] = args.width
        if args.height:
            payload["height"] = args.height

        url = await _submit_and_poll(self._api_key, args.model, payload, self._poll_interval, self._timeout)
        return MuApiImageOutput(image_url=url, model=args.model, prompt=args.prompt)


class MuApiVideoTool(BaseTool[MuApiVideoInput, MuApiVideoOutput]):
    """Generate videos using muapi.ai — a unified API for 400+ video models.

    Supports Veo3, Kling, Wan, Seedance, Runway, Pixverse, Sora, HunyuanVideo, and more.

    Args:
        api_key: muapi.ai API key. Get one at https://muapi.ai/dashboard/api-keys
        poll_interval: Seconds between status polls (default 3.0)
        timeout: Max seconds to wait for generation (default 600)
    """

    component_type = "tool"
    component_version = 1
    component_config_schema = MuApiVideoInput

    def __init__(self, api_key: str, poll_interval: float = 3.0, timeout: float = 600.0) -> None:
        super().__init__(
            args_type=MuApiVideoInput,
            return_type=MuApiVideoOutput,
            name="muapi_generate_video",
            description=(
                "Generate a short video from a text prompt using muapi.ai. "
                "Supports Veo3, Kling, Wan, Seedance, Runway, Pixverse, Sora, and more. "
                "Returns the URL of the generated MP4 video."
            ),
        )
        self._api_key = api_key
        self._poll_interval = poll_interval
        self._timeout = timeout

    async def run(self, args: MuApiVideoInput, cancellation_token: CancellationToken) -> MuApiVideoOutput:
        payload: dict[str, Any] = {
            "prompt": args.prompt,
            "duration": args.duration,
            "aspect_ratio": args.aspect_ratio,
        }
        url = await _submit_and_poll(self._api_key, args.model, payload, self._poll_interval, self._timeout)
        return MuApiVideoOutput(video_url=url, model=args.model, prompt=args.prompt)
