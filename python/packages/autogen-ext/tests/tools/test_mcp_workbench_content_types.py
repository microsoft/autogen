"""McpWorkbench must not drop a tool result because of one content block it
doesn't know how to map yet.

Audio results and resource links are both things real servers return --
``@modelcontextprotocol/server-everything`` has a ``getTinyAudio`` tool, and
servers use resource links instead of inlining a resource. Both used to hit
``else: raise ValueError``, which turns the whole call into ``is_error=True``
and throws away the text the model actually needed.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from autogen_core import Image
from autogen_core.tools import AudioResultContent, ImageResultContent, TextResultContent
from mcp.types import AudioContent, CallToolResult, ImageContent, ResourceLink, TextContent

from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

# 1x1 transparent png
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
# 4 bytes of riff header, enough to prove the bytes survive base64 decoding
WAV = "UklGRg=="


def _workbench_with(content: list, is_error: bool = False) -> McpWorkbench:
    workbench = McpWorkbench(server_params=StdioServerParams(command="echo", args=["test"]))
    actor = AsyncMock()
    future: asyncio.Future[CallToolResult] = asyncio.Future()
    future.set_result(CallToolResult(content=content, isError=is_error))
    actor.call.return_value = future
    workbench._actor = actor  # type: ignore[reportPrivateUsage]
    return workbench


@pytest.mark.asyncio
async def test_call_tool_audio_content() -> None:
    workbench = _workbench_with(
        [
            TextContent(type="text", text="here is the beep"),
            AudioContent(type="audio", data=WAV, mimeType="audio/wav"),
        ]
    )

    result = await workbench.call_tool("getTinyAudio")

    assert not result.is_error
    assert len(result.result) == 2
    assert isinstance(result.result[0], TextResultContent)
    assert result.result[0].content == "here is the beep"
    audio = result.result[1]
    assert isinstance(audio, AudioResultContent)
    assert audio.content == b"RIFF"
    assert audio.mime_type == "audio/wav"
    # audio is summarised, not inlined, when the result is flattened to text
    assert "[Audio: audio/wav, 4 bytes]" in result.to_text()


@pytest.mark.asyncio
async def test_call_tool_resource_link() -> None:
    workbench = _workbench_with(
        [
            ResourceLink(
                type="resource_link",
                name="config.json",
                uri="file:///etc/config.json",
                mimeType="application/json",
            )
        ]
    )

    result = await workbench.call_tool("get_config")

    assert not result.is_error
    assert len(result.result) == 1
    link = result.result[0]
    assert isinstance(link, TextResultContent)
    assert "file:///etc/config.json" in link.content
    assert "config.json" in link.content


@pytest.mark.asyncio
async def test_call_tool_mixed_known_and_new_content_keeps_order() -> None:
    workbench = _workbench_with(
        [
            TextContent(type="text", text="one"),
            ImageContent(type="image", data=PNG, mimeType="image/png"),
            AudioContent(type="audio", data=WAV, mimeType="audio/wav"),
            TextContent(type="text", text="two"),
        ]
    )

    result = await workbench.call_tool("mixed")

    assert not result.is_error
    kinds = [type(part) for part in result.result]
    assert kinds == [TextResultContent, ImageResultContent, AudioResultContent, TextResultContent]
    assert isinstance(result.result[1].content, Image)


@pytest.mark.asyncio
async def test_call_tool_audio_error_result_still_reports_error() -> None:
    workbench = _workbench_with(
        [TextContent(type="text", text="decoder failed"), AudioContent(type="audio", data=WAV, mimeType="audio/wav")],
        is_error=True,
    )

    result = await workbench.call_tool("getTinyAudio")

    assert result.is_error
    assert "decoder failed" in result.to_text()


@pytest.mark.asyncio
async def test_call_tool_audio_with_bad_base64() -> None:
    workbench = _workbench_with([AudioContent(type="audio", data="not base64!!", mimeType="audio/wav")])

    result = await workbench.call_tool("getTinyAudio")

    assert result.is_error
    assert "not valid base64" in result.to_text()
