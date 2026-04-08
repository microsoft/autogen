from typing import Optional

from autogen_core.tools import BaseTool

from ._audio_separation import AudioSeparationArgs, CambAudioSeparationTool
from ._text_to_sound import CambTextToSoundTool, TextToSoundArgs
from ._tts import CambTTSTool, TTSArgs
from ._transcription import CambTranscriptionTool, TranscriptionArgs
from ._translated_tts import CambTranslatedTTSTool, TranslatedTTSArgs
from ._translation import CambTranslationTool, TranslationArgs
from ._voice_clone import CambVoiceCloneTool, VoiceCloneArgs
from ._voice_list import CambVoiceListTool, VoiceListArgs


class CambAIToolkit:
    """Factory class to create all CAMB.AI tools with shared configuration.

    Creates all 8 CAMB.AI tools with shared API key, base URL, and timeout settings.
    Use the ``include_*`` flags to selectively enable or disable specific tools.

    .. note::
        This toolkit requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambAIToolkit, TTSArgs

        async def main():
            toolkit = CambAIToolkit(api_key="your-api-key")
            tools = toolkit.get_tools()
            # Use the TTS tool
            tts = tools[0]
            result = await tts.run(TTSArgs(text="Hello from AutoGen!"), CancellationToken())
            print(f"Audio saved to: {result}")

        asyncio.run(main())

    Args:
        api_key: CAMB.AI API key. Falls back to CAMB_API_KEY environment variable.
        base_url: Base URL for the CAMB.AI API.
        timeout: Request timeout in seconds.
        max_poll_attempts: Maximum number of polling attempts for async tasks.
        poll_interval: Interval between polling attempts in seconds.
        include_tts: Include the text-to-speech tool.
        include_translation: Include the translation tool.
        include_transcription: Include the transcription tool.
        include_translated_tts: Include the translated text-to-speech tool.
        include_voice_clone: Include the voice cloning tool.
        include_voice_list: Include the voice listing tool.
        include_text_to_sound: Include the text-to-sound tool.
        include_audio_separation: Include the audio separation tool.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
        include_tts: bool = True,
        include_translation: bool = True,
        include_transcription: bool = True,
        include_translated_tts: bool = True,
        include_voice_clone: bool = True,
        include_voice_list: bool = True,
        include_text_to_sound: bool = True,
        include_audio_separation: bool = True,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._max_poll_attempts = max_poll_attempts
        self._poll_interval = poll_interval
        self._include_tts = include_tts
        self._include_translation = include_translation
        self._include_transcription = include_transcription
        self._include_translated_tts = include_translated_tts
        self._include_voice_clone = include_voice_clone
        self._include_voice_list = include_voice_list
        self._include_text_to_sound = include_text_to_sound
        self._include_audio_separation = include_audio_separation

    def _make_kwargs(self) -> dict:
        return {
            "api_key": self._api_key,
            "base_url": self._base_url,
            "timeout": self._timeout,
            "max_poll_attempts": self._max_poll_attempts,
            "poll_interval": self._poll_interval,
        }

    def get_tools(self) -> list[BaseTool]:  # type: ignore[type-arg]
        """Create and return the enabled CAMB.AI tools.

        Returns:
            A list of CAMB.AI tool instances configured with shared settings.
        """
        kwargs = self._make_kwargs()
        tools: list[BaseTool] = []  # type: ignore[type-arg]

        if self._include_tts:
            tools.append(CambTTSTool(**kwargs))
        if self._include_translation:
            tools.append(CambTranslationTool(**kwargs))
        if self._include_transcription:
            tools.append(CambTranscriptionTool(**kwargs))
        if self._include_translated_tts:
            tools.append(CambTranslatedTTSTool(**kwargs))
        if self._include_voice_clone:
            tools.append(CambVoiceCloneTool(**kwargs))
        if self._include_voice_list:
            tools.append(CambVoiceListTool(**kwargs))
        if self._include_text_to_sound:
            tools.append(CambTextToSoundTool(**kwargs))
        if self._include_audio_separation:
            tools.append(CambAudioSeparationTool(**kwargs))

        return tools
