"""Tests for autogen_ext.tools.voidly_pay.VoidlyPayTool.

Mocks the x402 round-trip so the tests run offline. We pin the wire
format we care about: the tool reads the ``voidly-credit`` accept option
from a 402 envelope, signs a transfer to ``recipient_did``, retries
with ``?quote_id=<id>``, and returns the resolved response.
"""

from __future__ import annotations

import json
import sys
import types
from typing import Any
from unittest.mock import MagicMock

import pytest
from autogen_core import CancellationToken, ComponentModel

from autogen_ext.tools.voidly_pay import VoidlyPayTool, VoidlyPayToolConfig


def _install_fake_voidly_pay(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Drop a fake `voidly_pay` module into sys.modules.

    `_build_client()` calls `from voidly_pay import VoidlyPay` and then
    `VoidlyPay(api_base=..., did=..., secret_base64=...)`. We return a
    MagicMock client whose `.pay(...)` records the call.
    """
    pay_client = MagicMock()
    pay_client.pay.return_value = {"transfer_id": "tx-deadbeef"}
    pay_client.did = "did:voidly:test"

    fake_module = types.ModuleType("voidly_pay")
    fake_module.VoidlyPay = MagicMock(return_value=pay_client)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "voidly_pay", fake_module)

    # Ensure the optional autogen extension isn't picked up so we exercise
    # the inline path.
    monkeypatch.setitem(sys.modules, "voidly_pay_autogen", None)

    return pay_client


class _FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(
        self,
        status_code: int,
        body: dict[str, Any] | str,
        content_type: str = "application/json",
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = {"content-type": content_type}
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self) -> Any:
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


def _install_fake_httpx(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[_FakeResponse],
    record: list[tuple[str, str, Any]],
) -> None:
    """Provide a fake `httpx.AsyncClient` returning queued responses."""
    queue = list(responses)

    class _FakeClient:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *_a: Any) -> None:
            return None

        async def request(
            self,
            method: str,
            url: str,
            json: Any = None,  # noqa: A002 - mirror httpx kw
            **_kwargs: Any,
        ) -> _FakeResponse:
            record.append((method, url, json))
            if not queue:
                raise AssertionError(f"No more queued responses for {method} {url}")
            return queue.pop(0)

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.AsyncClient = _FakeClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)


def test_tool_schema() -> None:
    tool = VoidlyPayTool(VoidlyPayToolConfig())
    schema = tool.schema
    assert schema["name"] == "voidly_pay_fetch"
    assert "description" in schema
    parameters = schema["parameters"]
    assert parameters["type"] == "object"
    assert "url" in parameters["properties"]
    assert "max_amount_credits" in parameters["properties"]


def test_component_round_trip() -> None:
    tool = VoidlyPayTool(VoidlyPayToolConfig(api_base="https://example.test"))
    dumped = tool.dump_component()
    assert dumped is not None
    restored = VoidlyPayTool.load_component(dumped, VoidlyPayTool)
    assert isinstance(restored, VoidlyPayTool)
    assert restored._config.api_base == "https://example.test"


@pytest.mark.asyncio
async def test_x402_round_trip_settles(monkeypatch: pytest.MonkeyPatch) -> None:
    pay_client = _install_fake_voidly_pay(monkeypatch)

    record: list[tuple[str, str, Any]] = []
    _install_fake_httpx(
        monkeypatch,
        [
            _FakeResponse(
                402,
                {
                    "schema": "voidly-pay-402/v1",
                    "accepts": [
                        {
                            "scheme": "voidly-credit",
                            "amount_micro": 1000,
                            "recipient_did": "did:voidly:server",
                            "quote_id": "quote-abc",
                            "expires_at": "2099-01-01T00:00:00Z",
                        }
                    ],
                },
            ),
            _FakeResponse(200, {"summary": "Anthropic builds Claude."}),
        ],
        record,
    )

    tool = VoidlyPayTool(
        VoidlyPayToolConfig(
            did="did:voidly:caller",
            secret_base64="AAAA",
            api_base="https://api.voidly.ai",
        )
    )
    args = tool.args_type().model_validate(
        {
            "url": "https://api.voidly.ai/v1/pay/wiki",
            "max_amount_credits": 0.01,
        }
    )
    result = await tool.run(args, CancellationToken())

    assert result.settled is True
    assert result.transfer_id == "tx-deadbeef"
    assert result.amount_micro == 1000
    assert result.recipient == "did:voidly:server"
    assert result.response_status == 200
    assert result.response == {"summary": "Anthropic builds Claude."}

    pay_client.pay.assert_called_once()
    pay_kwargs = pay_client.pay.call_args.kwargs
    assert pay_kwargs["to"] == "did:voidly:server"
    assert pay_kwargs["amount_micro"] == 1000
    assert pay_kwargs["memo"].endswith("quote-abc")

    # First call hit the bare URL, second call appended quote_id.
    assert len(record) == 2
    assert record[0][1] == "https://api.voidly.ai/v1/pay/wiki"
    assert "quote_id=quote-abc" in record[1][1]


@pytest.mark.asyncio
async def test_x402_blocks_when_over_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    pay_client = _install_fake_voidly_pay(monkeypatch)

    record: list[tuple[str, str, Any]] = []
    _install_fake_httpx(
        monkeypatch,
        [
            _FakeResponse(
                402,
                {
                    "accepts": [
                        {
                            "scheme": "voidly-credit",
                            "amount_micro": 5_000_000,  # $5 — way above cap
                            "recipient_did": "did:voidly:server",
                            "quote_id": "quote-xyz",
                            "expires_at": "2099-01-01T00:00:00Z",
                        }
                    ]
                },
            ),
        ],
        record,
    )

    tool = VoidlyPayTool(VoidlyPayToolConfig(did="did:voidly:caller", secret_base64="AAAA"))
    args = tool.args_type().model_validate(
        {
            "url": "https://api.example.com/expensive",
            "max_amount_credits": 0.01,
        }
    )
    result = await tool.run(args, CancellationToken())

    assert result.blocked_by_cap is True
    assert result.settled is False
    assert result.amount_micro == 5_000_000
    pay_client.pay.assert_not_called()


@pytest.mark.asyncio
async def test_non_402_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    pay_client = _install_fake_voidly_pay(monkeypatch)

    record: list[tuple[str, str, Any]] = []
    _install_fake_httpx(
        monkeypatch,
        [
            _FakeResponse(200, {"hello": "world"}),
        ],
        record,
    )

    tool = VoidlyPayTool(VoidlyPayToolConfig(did="did:voidly:caller", secret_base64="AAAA"))
    args = tool.args_type().model_validate({"url": "https://api.example.com/free"})
    result = await tool.run(args, CancellationToken())

    assert result.settled is False
    assert result.response_status == 200
    assert result.response == {"hello": "world"}
    pay_client.pay.assert_not_called()
