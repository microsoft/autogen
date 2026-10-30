import json
from typing import Optional

from autogen_core import CancellationToken
from pydantic import BaseModel, Field
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class VoiceCloneArgs(BaseModel):
    """Arguments for the CAMB.AI voice cloning tool."""

    voice_name: str = Field(
        ...,
        description="Name for the cloned voice.",
    )
    audio_file_path: str = Field(
        ...,
        description="Path to the audio file (2+ seconds) to clone the voice from.",
    )
    gender: int = Field(
        default=0,
        description="Gender code: 0=not known, 1=male, 2=female, 9=not applicable.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the voice.",
    )
    age: Optional[int] = Field(
        default=None,
        description="Age of the voice.",
    )
    language: Optional[int] = Field(
        default=None,
        description="Language ID for the voice.",
    )


class CambVoiceCloneTool(CambBaseTool[VoiceCloneArgs, str]):
    """Voice cloning tool using CAMB.AI.

    Clones a voice from an audio sample using the CAMB.AI voice cloning API.
    Returns a JSON string with the voice_id.

    .. note::
        This tool requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambVoiceCloneTool, VoiceCloneArgs

        async def main():
            tool = CambVoiceCloneTool(api_key="your-api-key")
            result = await tool.run(
                VoiceCloneArgs(
                    voice_name="My Voice",
                    audio_file_path="/path/to/sample.wav",
                ),
                CancellationToken(),
            )
            print(f"Voice cloned: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambVoiceCloneTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=VoiceCloneArgs,
            return_type=str,
            name="camb_voice_clone",
            description=(
                "Clone a voice from an audio sample using CAMB.AI. "
                "Returns JSON with the voice_id."
            ),
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: VoiceCloneArgs, cancellation_token: CancellationToken) -> str:
        client = self._get_client()

        with open(args.audio_file_path, "rb") as f:
            kwargs: dict = {
                "file": f,
                "voice_name": args.voice_name,
                "gender": args.gender,
            }
            if args.description:
                kwargs["description"] = args.description
            if args.age is not None:
                kwargs["age"] = args.age
            if args.language is not None:
                kwargs["language"] = args.language

            result = await client.voice_cloning.create_custom_voice(**kwargs)

        output = {
            "voice_id": getattr(result, "voice_id", None),
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
