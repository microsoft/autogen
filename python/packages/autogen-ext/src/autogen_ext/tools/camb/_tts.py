from typing import Optional

from autogen_core import CancellationToken
from pydantic import BaseModel, Field
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class TTSArgs(BaseModel):
    """Arguments for the CAMB.AI text-to-speech tool."""

    text: str = Field(
        ...,
        min_length=3,
        max_length=3000,
        description="The text to convert to speech (3-3000 characters).",
    )
    language: str = Field(
        default="en-us",
        description="BCP-47 language code for the output speech.",
    )
    voice_id: int = Field(
        default=147320,
        description="The voice ID to use for speech synthesis.",
    )
    speech_model: str = Field(
        default="mars-flash",
        description="The speech model to use: 'mars-flash', 'mars-pro', or 'mars-instruct'.",
    )
    user_instructions: Optional[str] = Field(
        default=None,
        description="Optional instructions for the speech model (mars-instruct only).",
    )


class CambTTSTool(CambBaseTool[TTSArgs, str]):
    """Text-to-speech tool using CAMB.AI.

    Converts text to speech audio using the CAMB.AI streaming TTS API.
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
        from autogen_ext.tools.camb import CambTTSTool, TTSArgs

        async def main():
            tool = CambTTSTool(api_key="your-api-key")
            result = await tool.run(
                TTSArgs(text="Hello from AutoGen!"),
                CancellationToken(),
            )
            print(f"Audio saved to: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambTTSTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=TTSArgs,
            return_type=str,
            name="camb_tts",
            description="Convert text to speech using CAMB.AI. Returns the file path to the generated audio.",
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: TTSArgs, cancellation_token: CancellationToken) -> str:
        from camb import StreamTtsOutputConfiguration

        client = self._get_client()

        kwargs: dict = {
            "text": args.text,
            "voice_id": args.voice_id,
            "language": args.language,
            "output_configuration": StreamTtsOutputConfiguration(),
            "speech_model": args.speech_model,
        }
        if args.user_instructions:
            kwargs["user_instructions"] = args.user_instructions

        chunks: list[bytes] = []
        async for chunk in client.text_to_speech.tts(**kwargs):
            chunks.append(chunk)

        audio_data = b"".join(chunks)
        if not audio_data:
            raise RuntimeError("CAMB.AI TTS returned no audio data.")

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
