from pathlib import Path

import pytest
import typer

from autogenstudio import cli


def test_ui_missing_auth_config_uses_config_exit_code() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        cli.ui(auth_config="/path/does/not/exist.yaml")
    assert exc_info.value.exit_code == cli.EXIT_CONFIG


def test_serve_missing_team_uses_config_exit_code() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        cli.serve(team="/path/does/not/exist.json")
    assert exc_info.value.exit_code == cli.EXIT_CONFIG


def test_ui_uvicorn_error_uses_runtime_exit_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "get_env_file_path", lambda: str(tmp_path / "env.tmp"))

    def _raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli.uvicorn, "run", _raise_runtime_error)

    with pytest.raises(typer.Exit) as exc_info:
        cli.ui()
    assert exc_info.value.exit_code == cli.EXIT_RUNTIME
