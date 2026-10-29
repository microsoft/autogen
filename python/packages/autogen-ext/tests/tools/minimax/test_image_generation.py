from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from autogen_core import CancellationToken
from pydantic import ValidationError

from autogen_ext.tools.minimax import MiniMaxImageGenerationTool


def _mock_client(monkeypatch: pytest.MonkeyPatch, response_body: dict[str, Any]) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=response_body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "autogen_ext.tools.minimax._image_generation.httpx.AsyncClient",
        lambda **kwargs: client,
    )
    return requests


@pytest.mark.asyncio
async def test_generates_url_results_for_global_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = _mock_client(
        monkeypatch,
        {
            "data": {"image_urls": ["https://example.test/generated.png"]},
            "metadata": {"success_count": 1, "failed_count": 0},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        },
    )
    tool = MiniMaxImageGenerationTool(api_key="test-key")

    result = await tool.run_json({"prompt": "A paper kite"}, CancellationToken())

    assert result.images == ["https://example.test/generated.png"]
    assert result.response_format == "url"
    assert result.success_count == 1
    assert requests[0].url == "https://api.minimax.io/v1/image_generation"
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert json.loads(requests[0].read()) == {
        "model": "image-01",
        "prompt": "A paper kite",
        "response_format": "url",
        "n": 1,
        "prompt_optimizer": False,
    }


@pytest.mark.asyncio
async def test_parses_base64_results_for_china_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = _mock_client(
        monkeypatch,
        {
            "data": {"image_base64": ["aW1hZ2UtYnl0ZXM="]},
            "metadata": {"success_count": "1", "failed_count": "0"},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        },
    )
    tool = MiniMaxImageGenerationTool(api_key="test-key", model="image-01-live", region="cn_zh")

    result = await tool.run_json(
        {"prompt": "An ink landscape", "response_format": "base64", "width": 1024, "height": 768},
        CancellationToken(),
    )

    assert result.images == ["aW1hZ2UtYnl0ZXM="]
    assert result.response_format == "base64"
    assert requests[0].url == "https://api.minimaxi.com/v1/image_generation"
    assert b'"model":"image-01-live"' in requests[0].read()


@pytest.mark.asyncio
async def test_raises_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_client(
        monkeypatch,
        {
            "data": {"image_urls": []},
            "base_resp": {"status_code": 1002, "status_msg": "rate limit"},
        },
    )
    tool = MiniMaxImageGenerationTool(api_key="test-key")

    with pytest.raises(RuntimeError, match="1002"):
        await tool.run_json({"prompt": "A paper kite"}, CancellationToken())


def test_validates_dimensions_and_component_round_trip() -> None:
    tool = MiniMaxImageGenerationTool(api_key="test-key", region="cn_zh")

    with pytest.raises(ValidationError, match="provided together"):
        tool.args_type().model_validate({"prompt": "A paper kite", "width": 1024})
    with pytest.raises(ValidationError, match="divisible by 8"):
        tool.args_type().model_validate({"prompt": "A paper kite", "width": 1025, "height": 1024})

    restored = MiniMaxImageGenerationTool.load_component(tool.dump_component(), MiniMaxImageGenerationTool)
    assert restored.dump_component().config["region"] == "cn_zh"
    assert restored.schema["name"] == "minimax_image_generation"
