from typing import Optional

from autogen_core import CancellationToken
from pydantic import BaseModel, Field
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class TextToSoundArgs(BaseModel):
    """Arguments for the CAMB.AI text-to-sound tool."""

    prompt: str = Field(
        ...,
        description="Text description of the sound or music to generate.",
    )
    duration: Optional[float] = Field(
        default=None,
        description="Duration of the generated audio in seconds.",
    )
    audio_type: Optional[str] = Field(
        default=None,
        description="Type of audio to generate: 'music' or 'sound'.",
    )


class CambTextToSoundTool(CambBaseTool[TextToSoundArgs, str]):
    """Text-to-sound generation tool using CAMB.AI.

    Generates sounds or music from text descriptions using the CAMB.AI API.
    Returns the file path to the generated audio file.

    .. note::
        This tool requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambTextToSoundTool, TextToSoundArgs

        async def main():
            tool = CambTextToSoundTool(api_key="your-api-key")
            result = await tool.run(
                TextToSoundArgs(prompt="Ocean waves crashing on a beach"),
                CancellationToken(),
            )
            print(f"Audio saved to: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambTextToSoundTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=TextToSoundArgs,
            return_type=str,
            name="camb_text_to_sound",
            description=(
                "Generate sounds or music from text descriptions using CAMB.AI. "
                "Returns the file path to the generated audio."
            ),
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: TextToSoundArgs, cancellation_token: CancellationToken) -> str:
        client = self._get_client()

        kwargs: dict = {"prompt": args.prompt}
        if args.duration is not None:
            kwargs["duration"] = args.duration
        if args.audio_type is not None:
            kwargs["audio_type"] = args.audio_type

        task = await client.text_to_audio.create_text_to_audio(**kwargs)
        task_id = task.task_id

        status = await self._poll_task_status(
            client.text_to_audio.get_text_to_audio_status,
            task_id,
        )

        run_id = status.run_id

        chunks: list[bytes] = []
        async for chunk in client.text_to_audio.get_text_to_audio_result(run_id):
            chunks.append(chunk)

        audio_data = b"".join(chunks)
        if not audio_data:
            raise RuntimeError("CAMB.AI text-to-sound returned no audio data.")

        fmt = self._detect_audio_format(audio_data)
        if fmt == "wav" and audio_data[:4] != b"RIFF":
            audio_data = self._add_wav_header(audio_data)
        return self._save_audio(audio_data, fmt)

    @classmethod
    def _from_config(cls, config: CambToolConfig) -> Self:
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_poll_attempts=config.max_poll_attempts,
            poll_interval=config.poll_interval,
        )
