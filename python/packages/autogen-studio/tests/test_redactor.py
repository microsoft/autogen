import pytest
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    FunctionExecutionResult,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
)

from autogenstudio.datamodel.types import (
    EnvironmentVariable,
    LLMCallEventMessage,
    RedactionConfig,
    TeamResult,
)
from autogenstudio.utils.redactor import SensitiveDataRedactor


def test_redact_api_keys():
    """Verify built-in credential patterns are sanitized."""
    redactor = SensitiveDataRedactor(config=RedactionConfig(enabled=True, replacement="[REDACTED]"))

    test_samples = [
        ("sk-123456789012345678901234", "[REDACTED]"),
        ("sk-proj-abcdef1234567890123456789012", "[REDACTED]"),
        ("sk-ant-abcdef123456789012345678", "[REDACTED]"),
        ("ghp_abcdefghijklmnopqrstuvwxyz123456", "[REDACTED]"),
        ("AKIAIOSFODNN7EXAMPLE", "[REDACTED]"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "[REDACTED]"),
    ]

    for raw, expected in test_samples:
        result = redactor.redact_text(f"Secret: {raw} inside text.")
        assert expected in result
        assert raw not in result


def test_redact_env_vars():
    """Verify secrets from EnvironmentVariable instances are sanitized."""
    env_vars = [
        EnvironmentVariable(
            name="CUSTOM_DB_PASS",
            value="p@ssw0rd_secret_9988!",
            type="secret",
        ),
        EnvironmentVariable(
            name="INTERNAL_API_KEY",
            value="internal_secret_token_val_456",
            type="string",
        ),
    ]

    redactor = SensitiveDataRedactor(
        config=RedactionConfig(enabled=True, redact_env_vars=True, replacement="[REDACTED]"),
        env_vars=env_vars,
    )

    text = "Connecting with p@ssw0rd_secret_9988! and key internal_secret_token_val_456"
    sanitized = redactor.redact_text(text)

    assert "p@ssw0rd_secret_9988!" not in sanitized
    assert "internal_secret_token_val_456" not in sanitized
    assert sanitized.count("[REDACTED]") == 2


def test_redact_custom_patterns():
    """Verify user-configured custom regex patterns are sanitized."""
    config = RedactionConfig(
        enabled=True,
        custom_patterns=[r"corp-token-[0-9]{4,8}"],
        replacement="[MASKED]",
    )
    redactor = SensitiveDataRedactor(config=config)

    text = "Access granted with corp-token-998822 to internal server"
    sanitized = redactor.redact_text(text)

    assert "corp-token-998822" not in sanitized
    assert "[MASKED]" in sanitized


def test_redact_disabled():
    """Verify that sensitive data is preserved when redaction is disabled."""
    config = RedactionConfig(enabled=False)
    redactor = SensitiveDataRedactor(config=config)

    raw = "sk-proj-abcdef1234567890123456789012"
    assert redactor.redact_text(raw) == raw


def test_redact_messages():
    """Verify message models (TextMessage, StopMessage, MultiModalMessage) are sanitized."""
    redactor = SensitiveDataRedactor(config=RedactionConfig(enabled=True, replacement="[REDACTED]"))

    # TextMessage
    text_msg = TextMessage(source="agent", content="Leaked: sk-proj-1234567890123456789012")
    redacted_text = redactor.redact_message(text_msg)
    assert isinstance(redacted_text, TextMessage)
    assert "[REDACTED]" in redacted_text.content
    assert "sk-proj-1234567890123456789012" not in redacted_text.content

    # StopMessage
    stop_msg = StopMessage(source="system", content="Finished with ghp_abcdefghijklmnopqrstuvwxyz123456")
    redacted_stop = redactor.redact_message(stop_msg)
    assert isinstance(redacted_stop, StopMessage)
    assert "[REDACTED]" in redacted_stop.content

    # MultiModalMessage
    mm_msg = MultiModalMessage(source="agent", content=["Key: sk-ant-1234567890abcdef12345678"])
    redacted_mm = redactor.redact_message(mm_msg)
    assert isinstance(redacted_mm, MultiModalMessage)
    assert "[REDACTED]" in redacted_mm.content[0]


def test_redact_tool_execution_events():
    """Verify tool execution outputs containing exposed environment secrets are sanitized."""
    env_vars = [EnvironmentVariable(name="API_TOKEN", value="super_sensitive_token_777", type="secret")]
    redactor = SensitiveDataRedactor(config=RedactionConfig(enabled=True), env_vars=env_vars)

    tool_event = ToolCallExecutionEvent(
        source="bash_tool",
        content=[
            FunctionExecutionResult(
                name="bash",
                call_id="call_1",
                content="Output: API_TOKEN=super_sensitive_token_777 sk-proj-1234567890123456789012",
            )
        ],
    )

    redacted_event = redactor.redact_message(tool_event)
    assert isinstance(redacted_event, ToolCallExecutionEvent)
    result_content = redacted_event.content[0].content
    assert "super_sensitive_token_777" not in result_content
    assert "sk-proj-1234567890123456789012" not in result_content
    assert "[REDACTED]" in result_content


def test_redact_dict_and_team_result():
    """Verify nested dictionary and TeamResult structures are recursively sanitized."""
    redactor = SensitiveDataRedactor(config=RedactionConfig(enabled=True, replacement="[REDACTED]"))

    raw_dict = {
        "status": "success",
        "nested": {
            "key": "sk-proj-1234567890123456789012",
            "items": ["safe", "ghp_abcdefghijklmnopqrstuvwxyz123456"],
        },
    }

    sanitized_dict = redactor.redact_dict(raw_dict)
    assert sanitized_dict["nested"]["key"] == "[REDACTED]"
    assert sanitized_dict["nested"]["items"][1] == "[REDACTED]"
    assert sanitized_dict["nested"]["items"][0] == "safe"

    # TeamResult
    task_res = TaskResult(
        messages=[TextMessage(source="user", content="Here is sk-proj-1234567890123456789012")],
        stop_reason="Finished",
    )
    team_res = TeamResult(task_result=task_res, usage="10 tokens", duration=1.5)
    redacted_tr = redactor.redact_message(team_res)

    assert isinstance(redacted_tr, TeamResult)
    assert "[REDACTED]" in redacted_tr.task_result.messages[0].content
    assert "sk-proj-1234567890123456789012" not in redacted_tr.task_result.messages[0].content
