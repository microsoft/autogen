"""Tests for PlasmateFetchTool."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from autogen_core import CancellationToken, Component

from autogen_ext.tools.plasmate import (
    PlasmateFetchTool,
    PlasmateFetchToolArgs,
    PlasmateFetchToolConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: bytes = b"# Page\n\nContent.", stderr: bytes = b"", returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


def _patch_binary():
    return patch(
        "autogen_ext.tools.plasmate._plasmate_tool._find_plasmate",
        return_value="/usr/local/bin/plasmate",
    )


def _patch_subprocess(proc):
    return patch(
        "asyncio.create_subprocess_exec",
        AsyncMock(return_value=proc),
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_defaults(self) -> None:
        tool = PlasmateFetchTool()
        assert tool.name == "plasmate_fetch"
        assert tool.server_params.output_format == "markdown"
        assert tool.server_params.timeout == 30
        assert tool.server_params.selector is None
        assert tool.server_params.extra_headers == {}
        assert tool.server_params.fixed_url is None
        assert "compact" in tool.description.lower() or "compact" in tool.server_params.description.lower()

    def test_custom_name_and_description(self) -> None:
        tool = PlasmateFetchTool(name="my_fetcher", description="Custom description")
        assert tool.name == "my_fetcher"
        assert tool.description == "Custom description"

    def test_custom_format(self) -> None:
        tool = PlasmateFetchTool(output_format="text")
        assert tool.server_params.output_format == "text"

    def test_all_valid_formats(self) -> None:
        for fmt in ("markdown", "text", "som", "links"):
            tool = PlasmateFetchTool(output_format=fmt)  # type: ignore[arg-type]
            assert tool.server_params.output_format == fmt

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="output_format must be one of"):
            PlasmateFetchTool(output_format="html")  # type: ignore[arg-type]

    def test_fixed_url(self) -> None:
        tool = PlasmateFetchTool(fixed_url="https://example.com")
        assert tool.server_params.fixed_url == "https://example.com"

    def test_extra_headers(self) -> None:
        tool = PlasmateFetchTool(extra_headers={"Authorization": "Bearer tok"})
        assert tool.server_params.extra_headers == {"Authorization": "Bearer tok"}

    def test_selector(self) -> None:
        tool = PlasmateFetchTool(selector="main")
        assert tool.server_params.selector == "main"


# ---------------------------------------------------------------------------
# Component (de)serialisation
# ---------------------------------------------------------------------------


class TestComponent:
    def test_is_component(self) -> None:
        tool = PlasmateFetchTool()
        assert isinstance(tool, Component)

    def test_dump_load_roundtrip(self) -> None:
        original = PlasmateFetchTool(
            name="custom",
            output_format="text",
            timeout=60,
            selector="article",
            extra_headers={"Accept-Language": "en-US"},
            fixed_url="https://example.com",
        )

        dumped = original.dump_component()
        assert dumped is not None

        loaded = PlasmateFetchTool.load_component(dumped, PlasmateFetchTool)
        assert loaded.server_params.name == "custom"
        assert loaded.server_params.output_format == "text"
        assert loaded.server_params.timeout == 60
        assert loaded.server_params.selector == "article"
        assert loaded.server_params.extra_headers == {"Accept-Language": "en-US"}
        assert loaded.server_params.fixed_url == "https://example.com"

    def test_to_config_returns_copy(self) -> None:
        tool = PlasmateFetchTool(timeout=42)
        config = tool._to_config()
        assert config.timeout == 42
        # Mutating the returned config must not affect the tool
        config.timeout = 999
        assert tool.server_params.timeout == 42

    def test_from_config_creates_equivalent_tool(self) -> None:
        config = PlasmateFetchToolConfig(
            name="test",
            output_format="som",
            timeout=15,
            selector=None,
            extra_headers={},
            fixed_url=None,
        )
        tool = PlasmateFetchTool._from_config(config)
        assert tool.server_params.output_format == "som"
        assert tool.server_params.timeout == 15


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------


class TestBuildCmd:
    def test_basic_cmd(self) -> None:
        tool = PlasmateFetchTool()
        with _patch_binary():
            cmd = tool._build_cmd("https://example.com")
        assert cmd[0] == "/usr/local/bin/plasmate"
        assert "fetch" in cmd
        assert "https://example.com" in cmd
        assert "--format" in cmd
        assert "markdown" in cmd
        assert "--timeout" in cmd
        assert "30000" in cmd  # converted to ms

    def test_selector_added(self) -> None:
        tool = PlasmateFetchTool(selector="main")
        with _patch_binary():
            cmd = tool._build_cmd("https://example.com")
        assert "--selector" in cmd
        assert cmd[cmd.index("--selector") + 1] == "main"

    def test_extra_headers_added(self) -> None:
        tool = PlasmateFetchTool(extra_headers={"X-Custom": "val"})
        with _patch_binary():
            cmd = tool._build_cmd("https://example.com")
        assert "--header" in cmd
        assert "X-Custom: val" in cmd[cmd.index("--header") + 1]

    def test_timeout_in_ms(self) -> None:
        tool = PlasmateFetchTool(timeout=60)
        with _patch_binary():
            cmd = tool._build_cmd("https://example.com")
        assert "60000" in cmd

    def test_missing_binary_raises_import_error(self) -> None:
        tool = PlasmateFetchTool()
        with patch(
            "autogen_ext.tools.plasmate._plasmate_tool._find_plasmate",
            return_value=None,
        ):
            with pytest.raises(ImportError, match="plasmate is required"):
                tool._build_cmd("https://example.com")


# ---------------------------------------------------------------------------
# run() — success paths
# ---------------------------------------------------------------------------


class TestRun:
    @pytest.mark.asyncio
    async def test_successful_fetch(self) -> None:
        tool = PlasmateFetchTool()
        proc = _make_proc(stdout=b"# Heading\n\nBody")
        with _patch_binary(), _patch_subprocess(proc):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://example.com"),
                CancellationToken(),
            )
        assert "# Heading" in result
        assert "Body" in result

    @pytest.mark.asyncio
    async def test_uses_fixed_url_when_set(self) -> None:
        tool = PlasmateFetchTool(fixed_url="https://locked.example.com")
        proc = _make_proc(stdout=b"locked content")
        captured_cmd: dict = {}

        async def fake_exec(*args, **kwargs):
            captured_cmd["args"] = args
            return proc

        with _patch_binary(), patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://ignored.example.com"),
                CancellationToken(),
            )

        assert "locked content" in result
        assert "https://locked.example.com" in captured_cmd["args"]
        assert "https://ignored.example.com" not in captured_cmd["args"]

    @pytest.mark.asyncio
    async def test_text_format(self) -> None:
        tool = PlasmateFetchTool(output_format="text")
        proc = _make_proc(stdout=b"plain text")
        with _patch_binary(), _patch_subprocess(proc):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://example.com"),
                CancellationToken(),
            )
        assert "plain text" in result

    @pytest.mark.asyncio
    async def test_som_format(self) -> None:
        som = b'{"role":"document","children":[{"role":"heading","name":"Title"}]}'
        tool = PlasmateFetchTool(output_format="som")
        proc = _make_proc(stdout=som)
        with _patch_binary(), _patch_subprocess(proc):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://example.com"),
                CancellationToken(),
            )
        assert "heading" in result


# ---------------------------------------------------------------------------
# run() — error paths
# ---------------------------------------------------------------------------


class TestRunErrors:
    @pytest.mark.asyncio
    async def test_nonzero_exit_returns_error_string(self) -> None:
        tool = PlasmateFetchTool()
        proc = _make_proc(stdout=b"", stderr=b"network failure", returncode=1)
        with _patch_binary(), _patch_subprocess(proc):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://example.com"),
                CancellationToken(),
            )
        assert "Error" in result
        assert "exited 1" in result
        assert "network failure" in result

    @pytest.mark.asyncio
    async def test_timeout_returns_error_string(self) -> None:
        tool = PlasmateFetchTool(timeout=1)

        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        proc = MagicMock()
        proc.communicate = slow_communicate
        proc.kill = MagicMock()
        proc.wait = AsyncMock()

        with _patch_binary(), _patch_subprocess(proc):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://example.com"),
                CancellationToken(),
            )
        assert "timed out" in result
        proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_stdout_returns_warning(self) -> None:
        tool = PlasmateFetchTool()
        proc = _make_proc(stdout=b"")
        with _patch_binary(), _patch_subprocess(proc):
            result = await tool.run(
                PlasmateFetchToolArgs(url="https://example.com"),
                CancellationToken(),
            )
        assert "Warning" in result or "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_binary_raises_import_error(self) -> None:
        tool = PlasmateFetchTool()
        with patch(
            "autogen_ext.tools.plasmate._plasmate_tool._find_plasmate",
            return_value="/usr/local/bin/plasmate",
        ), patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(ImportError, match="plasmate is required"):
                await tool.run(
                    PlasmateFetchToolArgs(url="https://example.com"),
                    CancellationToken(),
                )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_schema_has_url_field(self) -> None:
        tool = PlasmateFetchTool()
        schema = tool.schema
        assert "parameters" in schema
        assert "url" in schema["parameters"]["properties"]

    def test_schema_url_is_required(self) -> None:
        tool = PlasmateFetchTool()
        schema = tool.schema
        assert "url" in schema["parameters"]["required"]
