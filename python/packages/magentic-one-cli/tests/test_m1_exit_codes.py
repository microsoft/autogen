import asyncio
import sys

import pytest
from magentic_one_cli import _m1


def test_missing_task_exits_with_usage_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["m1"])
    with pytest.raises(SystemExit) as exc_info:
        _m1.main()
    assert exc_info.value.code == _m1.EXIT_USAGE


def test_missing_config_file_exits_with_config_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["m1", "--config", "/path/does/not/exist.yaml", "demo task"],
    )
    with pytest.raises(SystemExit) as exc_info:
        _m1.main()
    assert exc_info.value.code == _m1.EXIT_CONFIG


def test_runtime_failure_exits_with_runtime_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["m1", "demo task"])

    def _raise_runtime_error(coro, *_args, **_kwargs):
        coro.close()
        raise RuntimeError("boom")

    monkeypatch.setattr(asyncio, "run", _raise_runtime_error)

    with pytest.raises(SystemExit) as exc_info:
        _m1.main()
    assert exc_info.value.code == _m1.EXIT_RUNTIME
