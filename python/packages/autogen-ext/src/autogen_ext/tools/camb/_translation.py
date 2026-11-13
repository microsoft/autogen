from typing import Optional

from autogen_core import CancellationToken
from pydantic import BaseModel, Field
from typing_extensions import Self

from ._base import CambBaseTool
from ._config import CambToolConfig


class TranslationArgs(BaseModel):
    """Arguments for the CAMB.AI translation tool."""

    text: str = Field(
        ...,
        description="The text to translate.",
    )
    source_language: int = Field(
        ...,
        description="Source language ID (CAMB.AI language code).",
    )
    target_language: int = Field(
        ...,
        description="Target language ID (CAMB.AI language code).",
    )
    formality: Optional[int] = Field(
        default=None,
        description="Formality level: 1 for formal, 2 for informal.",
    )


class CambTranslationTool(CambBaseTool[TranslationArgs, str]):
    """Text translation tool using CAMB.AI.

    Translates text between languages using the CAMB.AI streaming translation API.
    Returns the translated text string.

    .. note::
        This tool requires the :code:`camb` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[camb]"

    Example usage:

    .. code-block:: python

        import asyncio
        from autogen_core import CancellationToken
        from autogen_ext.tools.camb import CambTranslationTool, TranslationArgs

        async def main():
            tool = CambTranslationTool(api_key="your-api-key")
            result = await tool.run(
                TranslationArgs(text="Hello world", source_language=1, target_language=76),
                CancellationToken(),
            )
            print(f"Translated: {result}")

        asyncio.run(main())
    """

    component_provider_override = "autogen_ext.tools.camb.CambTranslationTool"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_poll_attempts: int = 60,
        poll_interval: float = 2.0,
    ) -> None:
        super().__init__(
            args_type=TranslationArgs,
            return_type=str,
            name="camb_translation",
            description="Translate text between languages using CAMB.AI. Returns the translated text.",
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_poll_attempts=max_poll_attempts,
            poll_interval=poll_interval,
        )

    async def run(self, args: TranslationArgs, cancellation_token: CancellationToken) -> str:
        from camb.core.api_error import ApiError

        client = self._get_client()

        kwargs: dict = {
            "text": args.text,
            "source_language": args.source_language,
            "target_language": args.target_language,
        }
        if args.formality is not None:
            kwargs["formality"] = args.formality

        try:
            result = await client.translation.translation_stream(**kwargs)
            return str(result)
        except ApiError as e:
            # SDK quirk: successful translations may raise ApiError with status 200
            if e.status_code == 200 and e.body:
                return str(e.body)
            raise

    @classmethod
    def _from_config(cls, config: CambToolConfig) -> Self:
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_poll_attempts=config.max_poll_attempts,
            poll_interval=config.poll_interval,
        )
