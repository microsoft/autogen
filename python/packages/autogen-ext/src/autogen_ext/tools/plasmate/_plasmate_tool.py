"""PlasmateFetchTool — fetch web pages as compact, LLM-ready content.

Uses Plasmate (https://github.com/plasmate-labs/plasmate), an open-source Rust
browser engine, instead of raw HTTP + HTML parsing or a full headless Chrome.
Plasmate strips navigation, ads, cookie banners, and boilerplate before content
reaches the agent — typically returning 10-100x fewer tokens than raw HTML.

This tool is a lightweight alternative for agents that only need to read pages.
For interactive browsing of JavaScript-heavy SPAs, use ``MultimodalWebSurfer``
from :mod:`autogen_ext.agents.web_surfer`.
"""

import asyncio
import shutil
from typing import Any, Literal, Optional

from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing_extensions import Self

_VALID_FORMATS = ("markdown", "text", "som", "links")

_INSTALL_MSG = (
    "plasmate is required for PlasmateFetchTool. "
    "Install it with: pip install -U 'autogen-ext[plasmate-tool]'\n"
    "Docs: https://plasmate.app"
)


def _find_plasmate() -> Optional[str]:
    """Locate the plasmate binary on PATH."""
    path = shutil.which("plasmate")
    if path:
        return path
    try:
        import plasmate as _p  # noqa: F401
        return shutil.which("plasmate")
    except ImportError:
        return None


class PlasmateFetchToolArgs(BaseModel):
    """Input arguments for PlasmateFetchTool."""

    url: str = Field(description="The URL of the page to fetch.")


class PlasmateFetchToolConfig(BaseModel):
    """Configuration for PlasmateFetchTool."""

    name: str = "plasmate_fetch"
    """The name of the tool."""

    description: str = (
        "Fetch a web page and return its content as compact, LLM-ready text. "
        "Uses Plasmate, a lightweight browser engine that strips navigation, "
        "ads, cookie banners, and boilerplate, returning 10-100x fewer tokens "
        "than raw HTML. Returns markdown by default."
    )
    """A description of the tool used by the model to decide when to call it."""

    output_format: Literal["markdown", "text", "som", "links"] = "markdown"
    """Output format Plasmate should emit. ``markdown`` is the best default for
    most LLM tasks. ``som`` returns the full Structured Object Model JSON,
    ``links`` returns extracted hyperlinks only."""

    timeout: int = 30
    """Per-request timeout in seconds. Defaults to 30."""

    selector: Optional[str] = None
    """Optional ARIA role or CSS id selector to scope extraction to a single
    region of the page (e.g. ``"main"`` or ``"#article"``)."""

    extra_headers: dict[str, str] = Field(default_factory=dict)
    """Optional HTTP headers forwarded with each Plasmate request."""

    fixed_url: Optional[str] = None
    """If set, this URL is used for every call and the agent's ``url`` argument
    is ignored. Useful for scoping a tool to a single data source."""


class PlasmateFetchTool(
    BaseTool[PlasmateFetchToolArgs, str],
    Component[PlasmateFetchToolConfig],
):
    """A tool that fetches a web page using Plasmate and returns LLM-ready content.

    Args:
        name (str): The name of the tool. Defaults to ``"plasmate_fetch"``.
        description (str): Description shown to the model.
        output_format (str): One of ``"markdown"``, ``"text"``, ``"som"``,
            ``"links"``. Defaults to ``"markdown"``.
        timeout (int): Per-request timeout in seconds. Defaults to ``30``.
        selector (str, optional): ARIA role or CSS id to scope extraction.
        extra_headers (dict, optional): HTTP headers forwarded with each request.
        fixed_url (str, optional): If set, the agent's ``url`` argument is
            ignored and this URL is used for every call.

    .. note::
        This tool requires the :code:`plasmate-tool` extra for the
        :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[plasmate-tool]"

    Example:

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.plasmate import PlasmateFetchTool


            async def main():
                fetch_tool = PlasmateFetchTool(output_format="markdown")

                model = OpenAIChatCompletionClient(model="gpt-4o-mini")
                assistant = AssistantAgent(
                    "researcher", model_client=model, tools=[fetch_tool]
                )

                response = await assistant.on_messages(
                    [
                        TextMessage(
                            content="Summarise the README at https://github.com/microsoft/autogen",
                            source="user",
                        )
                    ],
                    CancellationToken(),
                )
                print(response.chat_message)


            asyncio.run(main())

    Compared to ``ScrapeWebsiteTool``-style raw HTML readers, Plasmate returns
    pre-processed content that is typically **10-100x smaller**, directly
    reducing token cost. Measured across 45 real sites: 17.7x average
    compression, 77x peak.

    For JavaScript-heavy SPAs that require a real browser, use
    ``MultimodalWebSurfer`` from :mod:`autogen_ext.agents.web_surfer`.
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.plasmate.PlasmateFetchTool"
    component_config_schema = PlasmateFetchToolConfig

    def __init__(
        self,
        name: str = "plasmate_fetch",
        description: Optional[str] = None,
        output_format: Literal["markdown", "text", "som", "links"] = "markdown",
        timeout: int = 30,
        selector: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
        fixed_url: Optional[str] = None,
    ) -> None:
        if output_format not in _VALID_FORMATS:
            raise ValueError(
                f"output_format must be one of {_VALID_FORMATS}; got {output_format!r}"
            )

        # Build config (use defaults from PlasmateFetchToolConfig where applicable)
        config_kwargs: dict[str, Any] = {
            "name": name,
            "output_format": output_format,
            "timeout": timeout,
            "selector": selector,
            "extra_headers": extra_headers or {},
            "fixed_url": fixed_url,
        }
        if description is not None:
            config_kwargs["description"] = description

        self.server_params = PlasmateFetchToolConfig(**config_kwargs)

        super().__init__(
            args_type=PlasmateFetchToolArgs,
            return_type=str,
            name=self.server_params.name,
            description=self.server_params.description,
        )

    # ------------------------------------------------------------------
    # Component (de)serialisation
    # ------------------------------------------------------------------

    def _to_config(self) -> PlasmateFetchToolConfig:
        return self.server_params.model_copy()

    @classmethod
    def _from_config(cls, config: PlasmateFetchToolConfig) -> Self:
        return cls(
            name=config.name,
            description=config.description,
            output_format=config.output_format,
            timeout=config.timeout,
            selector=config.selector,
            extra_headers=dict(config.extra_headers),
            fixed_url=config.fixed_url,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cmd(self, url: str) -> list[str]:
        plasmate_bin = _find_plasmate()
        if plasmate_bin is None:
            raise ImportError(_INSTALL_MSG)
        cmd: list[str] = [
            plasmate_bin,
            "fetch",
            url,
            "--format", self.server_params.output_format,
            "--timeout", str(self.server_params.timeout * 1000),  # plasmate uses ms
        ]
        if self.server_params.selector:
            cmd += ["--selector", self.server_params.selector]
        for key, value in self.server_params.extra_headers.items():
            cmd += ["--header", f"{key}: {value}"]
        return cmd

    # ------------------------------------------------------------------
    # BaseTool interface
    # ------------------------------------------------------------------

    async def run(
        self,
        args: PlasmateFetchToolArgs,
        cancellation_token: CancellationToken,
    ) -> str:
        """Fetch a URL with Plasmate and return its compact content."""
        url = self.server_params.fixed_url or args.url
        if not url:
            return "Error: no URL provided. Pass a `url` argument."

        cmd = self._build_cmd(url)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise ImportError(_INSTALL_MSG) from e

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.server_params.timeout + 5,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"Error: request to {url} timed out after {self.server_params.timeout}s."

        if proc.returncode != 0:
            stderr = stderr_bytes.decode("utf-8", errors="replace")[:300]
            return (
                f"Error fetching {url} (plasmate exited {proc.returncode}): {stderr}"
            )

        content = stdout_bytes.decode("utf-8", errors="replace").strip()
        if not content:
            return f"Warning: plasmate returned empty content for {url}."
        return content
