import json
from typing import Any, Optional

from autogen_core import CancellationToken
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class TranscriptionArgs(BaseModel):
    """Arguments for the CAMB.AI transcription tool."""

    language: int = Field(
        ...,
        description="Language ID for the audio content (CAMB.AI language code).",
    )
    audio_url: Optional[str] = Field(
        default=None,
        description="URL of the audio file to transcribe.",
    )
    audio_file_path: Optional[str] = Field(
        default=None,
        description="Local file path of the audio file to transcribe.",
    )

    @model_validator(mode="after")
    def _validate_audio_source(self) -> "TranscriptionArgs":
        if not self.audio_url and not self.audio_file_path:
            raise ValueError("Either audio_url or audio_file_path must be provided.")
        if self.audio_url and self.audio_file_path:
            raise ValueError("Only one of audio_url or audio_file_path should be provided.")
        return self


class CambTranscriptionTool(CambBaseTool[TranscriptionArgs, str]):
    """Speech-to-text transcription tool using CAMB.AI.

    Transcribes audio to text with speaker diarization using the CAMB.AI transcription API.
    Returns a JSON string with the transcription result.

    .. note::
        This tool requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambTranscriptionTool, TranscriptionArgs

        async def main():
            tool = CambTranscriptionTool(api_key="your-api-key")
            result = await tool.run(
                TranscriptionArgs(language=1, audio_file_path="/path/to/audio.wav"),
                CancellationToken(),
            )
            print(f"Transcription: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambTranscriptionTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=TranscriptionArgs,
            return_type=str,
            name="camb_transcription",
            description=(
                "Transcribe audio to text using CAMB.AI. Returns JSON with "
                "transcription segments (start, end, text, speaker)."
            ),
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: TranscriptionArgs, cancellation_token: CancellationToken) -> str:
        client = self._get_client()

        kwargs: dict[str, Any] = {"language": args.language}
        if args.audio_url:
            kwargs["media_url"] = args.audio_url
        elif args.audio_file_path:
            kwargs["media_file"] = open(args.audio_file_path, "rb")

        try:
            task = await client.transcription.create_transcription(**kwargs)
        finally:
            if "media_file" in kwargs:
                kwargs["media_file"].close()

        task_id = task.task_id

        status = await self._poll_task_status(
            client.transcription.get_transcription_task_status,
            task_id,
        )

        run_id = status.run_id
        result = await client.transcription.get_transcription_result(run_id)

        # Serialize the TranscriptionResult to JSON
        output: dict[str, Any] = {}
        if hasattr(result, "transcript") and result.transcript:
            output["transcript"] = [
                {
                    "start": getattr(seg, "start", 0),
                    "end": getattr(seg, "end", 0),
                    "text": getattr(seg, "text", ""),
                    "speaker": getattr(seg, "speaker", ""),
                }
                for seg in result.transcript
            ]

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
