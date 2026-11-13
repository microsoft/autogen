import json
from typing import Optional

from autogen_core import CancellationToken
from pydantic import BaseModel
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class VoiceListArgs(BaseModel):
    """Arguments for the CAMB.AI voice listing tool (no arguments required)."""

    pass


class CambVoiceListTool(CambBaseTool[VoiceListArgs, str]):
    """Voice listing tool using CAMB.AI.

    Lists all available voices from the CAMB.AI voice cloning API.
    Returns a JSON array of voice objects with id and voice_name.

    .. note::
        This tool requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambVoiceListTool, VoiceListArgs

        async def main():
            tool = CambVoiceListTool(api_key="your-api-key")
            result = await tool.run(VoiceListArgs(), CancellationToken())
            print(f"Available voices: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambVoiceListTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=VoiceListArgs,
            return_type=str,
            name="camb_voice_list",
            description="List available voices from CAMB.AI. Returns a JSON array of voice objects.",
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: VoiceListArgs, cancellation_token: CancellationToken) -> str:
        client = self._get_client()
        result = await client.voice_cloning.list_voices()

        voices = []
        if result:
            for voice in result:
                if isinstance(voice, dict):
                    voices.append({
                        "id": voice.get("id"),
                        "voice_name": voice.get("voice_name"),
                    })
                else:
                    voices.append({
                        "id": getattr(voice, "id", None),
                        "voice_name": getattr(voice, "voice_name", None),
                    })

        return json.dumps(voices)

    @classmethod
    def _from_config(cls, config: CambToolConfig) -> Self:
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_poll_attempts=config.max_poll_attempts,
            poll_interval=config.poll_interval,
        )
