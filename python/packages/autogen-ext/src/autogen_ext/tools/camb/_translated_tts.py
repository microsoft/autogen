from typing import Optional

import httpx
from autogen_core import CancellationToken
from pydantic import BaseModel, Field
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig

_DEFAULT_TTS_RESULT_URL = "https://client.camb.ai/apis/tts-result"


class TranslatedTTSArgs(BaseModel):
    """Arguments for the CAMB.AI translated text-to-speech tool."""

    text: str = Field(
        ...,
        description="The text to translate and convert to speech.",
    )
    source_language: int = Field(
        ...,
        description="Source language ID (CAMB.AI language code).",
    )
    target_language: int = Field(
        ...,
        description="Target language ID (CAMB.AI language code).",
    )
    voice_id: int = Field(
        default=147320,
        description="The voice ID to use for speech synthesis.",
    )
    formality: Optional[int] = Field(
        default=None,
        description="Formality level: 1 for formal, 2 for informal.",
    )


class CambTranslatedTTSTool(CambBaseTool[TranslatedTTSArgs, str]):
    """Translated text-to-speech tool using CAMB.AI.

    Translates text and converts it to speech in one step using the CAMB.AI API.
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
        from autogen_ext.tools.camb import CambTranslatedTTSTool, TranslatedTTSArgs

        async def main():
            tool = CambTranslatedTTSTool(api_key="your-api-key")
            result = await tool.run(
                TranslatedTTSArgs(
                    text="Hello world",
                    source_language=1,
                    target_language=76,
                ),
                CancellationToken(),
            )
            print(f"Audio saved to: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambTranslatedTTSTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=TranslatedTTSArgs,
            return_type=str,
            name="camb_translated_tts",
            description=(
                "Translate text and convert to speech in one step using CAMB.AI. "
                "Returns the file path to the generated audio."
            ),
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: TranslatedTTSArgs, cancellation_token: CancellationToken) -> str:
        client = self._get_client()

        kwargs: dict = {
            "text": args.text,
            "source_language": args.source_language,
            "target_language": args.target_language,
            "voice_id": args.voice_id,
        }
        if args.formality is not None:
            kwargs["formality"] = args.formality

        task = await client.translated_tts.create_translated_tts(**kwargs)
        task_id = task.task_id

        status = await self._poll_task_status(
            client.translated_tts.get_translated_tts_task_status,
            task_id,
        )

        run_id = status.run_id

        # SDK doesn't have a direct audio result method for translated TTS; fetch via HTTP
        url = f"{_DEFAULT_TTS_RESULT_URL}/{run_id}"
        api_key = self._get_api_key()
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(url, headers={"x-api-key": api_key})
            response.raise_for_status()
            audio_data = response.content

        if not audio_data:
            raise RuntimeError("CAMB.AI translated TTS returned no audio data.")

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
