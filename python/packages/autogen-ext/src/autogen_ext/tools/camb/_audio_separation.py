import json
from typing import Optional

from autogen_core import CancellationToken
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class AudioSeparationArgs(BaseModel):
    """Arguments for the CAMB.AI audio separation tool."""

    audio_url: Optional[str] = Field(
        default=None,
        description="URL of the audio file to separate.",
    )
    audio_file_path: Optional[str] = Field(
        default=None,
        description="Local file path of the audio file to separate.",
    )

    @model_validator(mode="after")
    def _validate_audio_source(self) -> "AudioSeparationArgs":
        if not self.audio_url and not self.audio_file_path:
            raise ValueError("Either audio_url or audio_file_path must be provided.")
        if self.audio_url and self.audio_file_path:
            raise ValueError("Only one of audio_url or audio_file_path should be provided.")
        return self


class CambAudioSeparationTool(CambBaseTool[AudioSeparationArgs, str]):
    """Audio separation tool using CAMB.AI.

    Separates vocals from background audio using the CAMB.AI audio separation API.
    Returns a JSON string with vocals and background URLs.

    .. note::
        This tool requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambAudioSeparationTool, AudioSeparationArgs

        async def main():
            tool = CambAudioSeparationTool(api_key="your-api-key")
            result = await tool.run(
                AudioSeparationArgs(audio_file_path="/path/to/audio.mp3"),
                CancellationToken(),
            )
            print(f"Separation result: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambAudioSeparationTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=AudioSeparationArgs,
            return_type=str,
            name="camb_audio_separation",
            description=(
                "Separate vocals from background audio using CAMB.AI. "
                "Returns JSON with vocals and background URLs."
            ),
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: AudioSeparationArgs, cancellation_token: CancellationToken) -> str:
        client = self._get_client()

        kwargs: dict = {}
        if args.audio_url:
            kwargs["media_url"] = args.audio_url
        elif args.audio_file_path:
            kwargs["media_file"] = open(args.audio_file_path, "rb")

        try:
            task = await client.audio_separation.create_audio_separation(**kwargs)
        finally:
            if "media_file" in kwargs:
                kwargs["media_file"].close()

        task_id = task.task_id

        status = await self._poll_task_status(
            client.audio_separation.get_audio_separation_status,
            task_id,
        )

        run_id = status.run_id
        result = await client.audio_separation.get_audio_separation_run_info(run_id)

        output = {
            "foreground_audio_url": getattr(result, "foreground_audio_url", None),
            "background_audio_url": getattr(result, "background_audio_url", None),
        }
        return json.dumps(output)

    @classmethod
    def _from_config(cls, config: CambToolConfig) -> Self:
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_poll_attempts=config.max_poll_attempts,
            poll_interval=config.poll_interval,
        )
