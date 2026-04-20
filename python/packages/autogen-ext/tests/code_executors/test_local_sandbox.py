# Tests for the opt-in ``sandbox`` parameter on LocalCommandLineCodeExecutor.
# See https://github.com/microsoft/autogen/issues/7462 for context.

import os
import sys
import warnings

import pytest
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.code_executors.local import (
    LocalCommandLineCodeExecutorConfig,
)


def test_sandbox_none_emits_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        LocalCommandLineCodeExecutor()

    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    user_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "DockerCommandLineCodeExecutor" in str(w.message)
    ]
    assert deprecations, "sandbox=None must emit a DeprecationWarning"
    assert not user_warnings, "legacy UserWarning should be replaced by DeprecationWarning when sandbox=None"


def test_sandbox_false_emits_no_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        LocalCommandLineCodeExecutor(sandbox=False)

    sandbox_related = [
        w
        for w in caught
        if "sandbox" in str(w.message).lower() or issubclass(w.category, DeprecationWarning)
    ]
    assert not sandbox_related, f"sandbox=False should not emit warnings, got: {[str(w.message) for w in caught]}"


def test_sandbox_true_no_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        LocalCommandLineCodeExecutor(sandbox=True)

    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not deprecations, "sandbox=True should not emit DeprecationWarning"


def test_config_round_trip_preserves_sandbox() -> None:
    for sandbox_value in (None, True, False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            executor = LocalCommandLineCodeExecutor(sandbox=sandbox_value, sandbox_memory_bytes=123456789)
        config = executor._to_config()
        assert config.sandbox == sandbox_value
        assert config.sandbox_memory_bytes == 123456789

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            rebuilt = LocalCommandLineCodeExecutor._from_config(config)
        assert rebuilt.sandbox == sandbox_value
        assert rebuilt._sandbox_memory_bytes == 123456789


def test_config_model_defaults() -> None:
    cfg = LocalCommandLineCodeExecutorConfig()
    assert cfg.sandbox is None
    assert cfg.sandbox_memory_bytes == 512 * 1024 * 1024


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: env scrub + rlimits")
@pytest.mark.asyncio
async def test_sandbox_true_scrubs_credential_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("FAKE_API_KEY", "xyz-should-not-leak")
    monkeypatch.setenv("HARMLESS_VAR", "keep-me")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        executor = LocalCommandLineCodeExecutor(work_dir=tmp_path, sandbox=True)

    result = await executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(
                language="bash",
                code='echo "API=${FAKE_API_KEY:-MISSING}"; echo "OK=${HARMLESS_VAR:-MISSING}"',
            )
        ],
        cancellation_token=CancellationToken(),
    )
    assert result.exit_code == 0, result.output
    assert "API=MISSING" in result.output, f"FAKE_API_KEY was not scrubbed. Output: {result.output!r}"
    assert "OK=keep-me" in result.output, f"HARMLESS_VAR should have been preserved. Output: {result.output!r}"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
@pytest.mark.asyncio
async def test_sandbox_false_preserves_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("FAKE_API_KEY", "xyz-should-be-visible")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        executor = LocalCommandLineCodeExecutor(work_dir=tmp_path, sandbox=False)

    result = await executor.execute_code_blocks(
        code_blocks=[CodeBlock(language="bash", code='echo "API=${FAKE_API_KEY:-MISSING}"')],
        cancellation_token=CancellationToken(),
    )
    assert result.exit_code == 0, result.output
    assert "API=xyz-should-be-visible" in result.output


def test_sandbox_true_imports_cleanly_on_windows() -> None:
    # Smoke test: on any platform, constructing with sandbox=True must not raise.
    # On Windows the Windows degrade path only logs a warning.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        executor = LocalCommandLineCodeExecutor(sandbox=True)
    assert executor.sandbox is True
