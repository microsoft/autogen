"""Tests for alternating role enforcement in messages sent to LLMs.

These tests cover the ensure_alternating_roles utility function and its
integration with AssistantAgent and SelectorGroupChat for models that
require strict alternating user-assistant message roles (e.g., DeepSeek R1,
Mistral).

See: https://github.com/microsoft/autogen/issues/5965
"""

import asyncio
from typing import Any, List, Mapping, Optional, Sequence, Union
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)

from autogen_agentchat.utils._utils import (
    ensure_alternating_roles,
    _get_role,
)


# ---------------------------------------------------------------------------
# Helper: role sequence extractor
# ---------------------------------------------------------------------------

def _roles(messages: Sequence[LLMMessage]) -> List[str]:
    """Return the role sequence of a message list."""
    return [_get_role(m) for m in messages]


# ===========================================================================
# 1. Basic alternation tests
# ===========================================================================

class TestEnsureAlternatingRolesBasic:
    """Basic tests for the ensure_alternating_roles function."""

    def test_empty_messages(self) -> None:
        """Empty input should produce empty output."""
        assert ensure_alternating_roles([]) == []

    def test_single_user_message(self) -> None:
        """A single user message should pass through unchanged."""
        msgs: List[LLMMessage] = [UserMessage(content="hello", source="user")]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], UserMessage)

    def test_single_assistant_message(self) -> None:
        """A single assistant message should pass through unchanged."""
        msgs: List[LLMMessage] = [AssistantMessage(content="hi", source="bot")]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)

    def test_already_alternating(self) -> None:
        """Messages that already alternate should be unchanged."""
        msgs: List[LLMMessage] = [
            UserMessage(content="hello", source="user"),
            AssistantMessage(content="hi", source="bot"),
            UserMessage(content="how are you?", source="user"),
            AssistantMessage(content="fine", source="bot"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 4
        assert _roles(result) == ["user", "assistant", "user", "assistant"]

    def test_system_messages_preserved(self) -> None:
        """Leading system messages should be preserved at the start."""
        msgs: List[LLMMessage] = [
            SystemMessage(content="You are helpful."),
            SystemMessage(content="Be concise."),
            UserMessage(content="hello", source="user"),
            AssistantMessage(content="hi", source="bot"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 4
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], SystemMessage)
        assert _roles(result) == ["system", "system", "user", "assistant"]


# ===========================================================================
# 2. Consecutive same-role merging tests
# ===========================================================================

class TestConsecutiveMerging:
    """Tests for merging consecutive same-role messages."""

    def test_consecutive_user_messages_merged(self) -> None:
        """Two consecutive user messages should be merged into one."""
        msgs: List[LLMMessage] = [
            UserMessage(content="hello", source="user"),
            UserMessage(content="world", source="user"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        assert "hello" in result[0].content  # type: ignore
        assert "world" in result[0].content  # type: ignore

    def test_consecutive_assistant_messages_merged(self) -> None:
        """Two consecutive assistant messages should be merged into one."""
        msgs: List[LLMMessage] = [
            AssistantMessage(content="I think", source="bot"),
            AssistantMessage(content="therefore I am", source="bot"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert "I think" in result[0].content  # type: ignore
        assert "therefore I am" in result[0].content  # type: ignore

    def test_three_consecutive_user_messages_merged(self) -> None:
        """Three consecutive user messages should all be merged."""
        msgs: List[LLMMessage] = [
            UserMessage(content="a", source="u1"),
            UserMessage(content="b", source="u2"),
            UserMessage(content="c", source="u3"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], UserMessage)
        content = result[0].content
        assert "a" in content and "b" in content and "c" in content  # type: ignore

    def test_three_consecutive_assistant_messages_merged(self) -> None:
        """Three consecutive assistant messages should all be merged."""
        msgs: List[LLMMessage] = [
            AssistantMessage(content="x", source="a1"),
            AssistantMessage(content="y", source="a2"),
            AssistantMessage(content="z", source="a3"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)

    def test_assistant_thought_merged(self) -> None:
        """Thoughts from consecutive assistant messages should be merged."""
        msgs: List[LLMMessage] = [
            AssistantMessage(content="reply1", source="bot", thought="thought1"),
            AssistantMessage(content="reply2", source="bot", thought="thought2"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert isinstance(result[0], AssistantMessage)
        assert result[0].thought is not None
        assert "thought1" in result[0].thought
        assert "thought2" in result[0].thought


# ===========================================================================
# 3. Function execution result handling
# ===========================================================================

class TestFunctionExecutionResults:
    """Tests for FunctionExecutionResultMessage handling."""

    def test_func_result_after_assistant_is_ok(self) -> None:
        """FunctionExecutionResultMessage after assistant should be fine (user-role)."""
        msgs: List[LLMMessage] = [
            AssistantMessage(content=[FunctionCall(id="1", arguments="{}", name="f")], source="bot"),
            FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content="ok", name="f", call_id="1")]
            ),
        ]
        result = ensure_alternating_roles(msgs)
        # assistant -> user (func result) is valid alternation
        roles = _roles(result)
        for i in range(1, len(roles)):
            if roles[i] != "system":
                assert roles[i] != roles[i - 1] or roles[i] == "system"

    def test_func_result_after_user_merged(self) -> None:
        """FunctionExecutionResultMessage after UserMessage should be merged (both user-role)."""
        msgs: List[LLMMessage] = [
            UserMessage(content="do something", source="user"),
            FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content="result", name="f", call_id="1")]
            ),
        ]
        result = ensure_alternating_roles(msgs)
        # Should be merged into one user message
        assert len(result) == 1
        assert _get_role(result[0]) == "user"

    def test_two_func_results_merged(self) -> None:
        """Two consecutive FunctionExecutionResultMessages should be merged."""
        msgs: List[LLMMessage] = [
            FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content="r1", name="f1", call_id="1")]
            ),
            FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content="r2", name="f2", call_id="2")]
            ),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 1
        assert _get_role(result[0]) == "user"


# ===========================================================================
# 4. Non-leading system message handling
# ===========================================================================

class TestNonLeadingSystemMessages:
    """Tests for system messages that appear in the middle of conversation."""

    def test_mid_conversation_system_converted_to_user(self) -> None:
        """System messages in the middle should be converted to user messages."""
        msgs: List[LLMMessage] = [
            UserMessage(content="hello", source="user"),
            AssistantMessage(content="hi", source="bot"),
            SystemMessage(content="New instruction"),
            AssistantMessage(content="ok", source="bot"),
        ]
        result = ensure_alternating_roles(msgs)
        roles = _roles(result)
        # The system message should be converted to user, maintaining alternation
        assert "system" not in roles[2:]  # No system after first two positions if they exist


# ===========================================================================
# 5. Complex / realistic scenarios
# ===========================================================================

class TestComplexScenarios:
    """Tests for complex real-world message sequences."""

    def test_multi_agent_conversation(self) -> None:
        """Simulate a multi-agent conversation where multiple assistants speak in sequence."""
        msgs: List[LLMMessage] = [
            SystemMessage(content="You coordinate agents."),
            UserMessage(content="Solve this problem", source="user"),
            AssistantMessage(content="Agent1: I'll analyze", source="agent1"),
            AssistantMessage(content="Agent2: I'll implement", source="agent2"),
            AssistantMessage(content="Agent3: I'll test", source="agent3"),
            UserMessage(content="Good teamwork!", source="user"),
        ]
        result = ensure_alternating_roles(msgs)
        roles = _roles(result)
        # After system messages, should strictly alternate
        non_system = [r for r in roles if r != "system"]
        for i in range(1, len(non_system)):
            assert non_system[i] != non_system[i - 1], (
                f"Consecutive same role at index {i}: {non_system}"
            )

    def test_tool_call_sequence(self) -> None:
        """Simulate: user -> assistant(tool_call) -> func_result -> assistant -> user."""
        msgs: List[LLMMessage] = [
            UserMessage(content="What's the weather?", source="user"),
            AssistantMessage(
                content=[FunctionCall(id="call1", arguments='{"city":"NYC"}', name="weather")],
                source="bot",
            ),
            FunctionExecutionResultMessage(
                content=[FunctionExecutionResult(content="Sunny, 72F", name="weather", call_id="call1")]
            ),
            AssistantMessage(content="The weather in NYC is sunny, 72F.", source="bot"),
            UserMessage(content="Thanks!", source="user"),
        ]
        result = ensure_alternating_roles(msgs)
        roles = _roles(result)
        non_system = [r for r in roles if r != "system"]
        for i in range(1, len(non_system)):
            assert non_system[i] != non_system[i - 1], (
                f"Consecutive same role at index {i}: {non_system}"
            )

    def test_deepseek_r1_typical_scenario(self) -> None:
        """Simulate typical DeepSeek R1 interaction with system + user messages."""
        msgs: List[LLMMessage] = [
            SystemMessage(content="You are a helpful assistant."),
            UserMessage(content="Hello", source="user"),
            AssistantMessage(content="Hi there!", source="assistant"),
            UserMessage(content="Tell me a joke", source="user"),
        ]
        result = ensure_alternating_roles(msgs)
        # Should pass through unchanged since it's already alternating
        assert len(result) == 4
        assert _roles(result) == ["system", "user", "assistant", "user"]

    def test_selector_retry_pattern(self) -> None:
        """Simulate selector group chat retry pattern with feedback messages."""
        msgs: List[LLMMessage] = [
            UserMessage(content="Select a speaker", source="user"),
            AssistantMessage(content="I pick agent_x", source="selector"),
            UserMessage(content="Invalid name, try again", source="user"),
            AssistantMessage(content="I pick agent_a", source="selector"),
            UserMessage(content="Invalid again", source="user"),
        ]
        result = ensure_alternating_roles(msgs)
        roles = _roles(result)
        for i in range(1, len(roles)):
            assert roles[i] != roles[i - 1]


# ===========================================================================
# 6. ModelFamily.requires_alternating_roles tests
# ===========================================================================

class TestModelFamilyRequiresAlternating:
    """Tests for the ModelFamily.requires_alternating_roles static method."""

    def test_r1_requires_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.R1) is True

    def test_mistral_requires_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.MISTRAL) is True

    def test_ministral_requires_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.MINISTRAL) is True

    def test_codestral_requires_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.CODESRAL) is True

    def test_pixtral_requires_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.PIXTRAL) is True

    def test_gpt4o_does_not_require_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.GPT_4O) is False

    def test_claude_does_not_require_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.CLAUDE_3_5_SONNET) is False

    def test_gemini_does_not_require_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.GEMINI_2_0_FLASH) is False

    def test_unknown_does_not_require_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.UNKNOWN) is False

    def test_llama_does_not_require_alternating(self) -> None:
        assert ModelFamily.requires_alternating_roles(ModelFamily.LLAMA_4_SCOUT) is False


# ===========================================================================
# 7. ModelInfo requires_alternating_roles field
# ===========================================================================

class TestModelInfoField:
    """Tests for the requires_alternating_roles field in ModelInfo."""

    def test_model_info_with_alternating_true(self) -> None:
        info: ModelInfo = {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.R1,
            "structured_output": False,
            "requires_alternating_roles": True,
        }
        assert info.get("requires_alternating_roles") is True

    def test_model_info_without_alternating_defaults_false(self) -> None:
        info: ModelInfo = {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.GPT_4O,
            "structured_output": False,
        }
        # Should default to False when not present
        assert info.get("requires_alternating_roles", False) is False

    def test_model_info_explicit_false(self) -> None:
        info: ModelInfo = {
            "vision": True,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
            "requires_alternating_roles": False,
        }
        assert info.get("requires_alternating_roles") is False


# ===========================================================================
# 8. Edge cases
# ===========================================================================

class TestEdgeCases:
    """Edge case tests for ensure_alternating_roles."""

    def test_only_system_messages(self) -> None:
        """Only system messages should be returned as-is."""
        msgs: List[LLMMessage] = [
            SystemMessage(content="sys1"),
            SystemMessage(content="sys2"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 2
        assert all(isinstance(m, SystemMessage) for m in result)

    def test_empty_content_messages(self) -> None:
        """Messages with empty content should still be handled."""
        msgs: List[LLMMessage] = [
            UserMessage(content="", source="user"),
            AssistantMessage(content="", source="bot"),
        ]
        result = ensure_alternating_roles(msgs)
        assert len(result) == 2

    def test_alternation_preserved_after_merge(self) -> None:
        """After merging, the overall alternation should be correct."""
        msgs: List[LLMMessage] = [
            UserMessage(content="a", source="u1"),
            UserMessage(content="b", source="u2"),
            AssistantMessage(content="c", source="bot"),
            AssistantMessage(content="d", source="bot"),
            UserMessage(content="e", source="u1"),
        ]
        result = ensure_alternating_roles(msgs)
        roles = _roles(result)
        non_system = [r for r in roles if r != "system"]
        for i in range(1, len(non_system)):
            assert non_system[i] != non_system[i - 1], (
                f"Consecutive same role at index {i}: {non_system}"
            )

    def test_large_message_sequence(self) -> None:
        """Test with a large number of messages to check performance."""
        msgs: List[LLMMessage] = []
        for i in range(100):
            msgs.append(UserMessage(content=f"user msg {i}", source="user"))
            msgs.append(UserMessage(content=f"user msg {i} extra", source="user"))
            msgs.append(AssistantMessage(content=f"bot msg {i}", source="bot"))
        result = ensure_alternating_roles(msgs)
        roles = _roles(result)
        non_system = [r for r in roles if r != "system"]
        for i in range(1, len(non_system)):
            assert non_system[i] != non_system[i - 1]

    def test_system_then_consecutive_assistants(self) -> None:
        """System message followed by consecutive assistants should be handled."""
        msgs: List[LLMMessage] = [
            SystemMessage(content="sys"),
            AssistantMessage(content="a1", source="bot1"),
            AssistantMessage(content="a2", source="bot2"),
        ]
        result = ensure_alternating_roles(msgs)
        assert isinstance(result[0], SystemMessage)
        # The two assistants should be merged
        non_system = [m for m in result if not isinstance(m, SystemMessage)]
        assert len(non_system) == 1
        assert isinstance(non_system[0], AssistantMessage)
