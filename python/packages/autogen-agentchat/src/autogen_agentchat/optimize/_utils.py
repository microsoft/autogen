"""Utility glue for turning AutoGen agents into DSPy-friendly modules."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    try:
        import dspy
    except ImportError:
        dspy = None

    from autogen_core.models import AssistantMessage, SystemMessage, UserMessage
    from autogen_core.models.base import ChatCompletionClient


def _check_dspy_available() -> None:
    """Check if DSPy is available and raise helpful error if not."""
    try:
        import dspy  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "DSPy is required for optimization but not installed. "
            "Please install it with: pip install dspy"
        ) from e


# --------------------------------------------------------------------- #
# 1.  LM adaptor –– AutoGen client  ➜  DSPy.LM
# --------------------------------------------------------------------- #
class AutoGenLM:
    """Adapts an AutoGen ChatCompletionClient to DSPy.LM interface."""

    def __init__(self, client: "ChatCompletionClient") -> None:
        _check_dspy_available()
        import dspy
        
        self.client = client
        self.model = getattr(client, "model", "unknown")
        # Call dspy.LM's init
        self._dspy_lm = dspy.LM(model=self.model)

    async def _acall(self, messages: List[Dict[str, str]], **kw: Any) -> str:
        """Convert DSPy messages to AutoGen format and call the client."""
        from autogen_core.models import AssistantMessage, SystemMessage, UserMessage
        
        autogen_msgs = []
        for m in messages:
            role, content = m["role"], m["content"]
            if role == "user":
                autogen_msgs.append(UserMessage(content=content))
            elif role == "assistant":
                autogen_msgs.append(AssistantMessage(content=content))
            else:
                autogen_msgs.append(SystemMessage(content=content))
        
        resp = await self.client.create(autogen_msgs, **kw)
        return resp.content

    def __call__(self, messages: List[Dict[str, str]], **kw: Any) -> str:
        """Synchronous interface for DSPy compatibility."""
        return asyncio.run(self._acall(messages, **kw))
    
    def __getattr__(self, name: str) -> Any:
        """Delegate to DSPy LM for compatibility."""
        return getattr(self._dspy_lm, name)


# --------------------------------------------------------------------- #
# 2.  DSPy module wrapper around an existing Agent
# --------------------------------------------------------------------- #
class DSPyAgentWrapper:
    """
    Exposes `agent.system_message` and each tool description as learnable prompts.
    """

    def __init__(self, agent: Any) -> None:
        _check_dspy_available()
        import dspy
        
        self._agent = agent

        # Turn system prompt & each tool description into learnable strings
        system_message = getattr(agent, "system_message", None)
        if system_message is None:
            # For AssistantAgent, system message is in _system_messages
            system_messages = getattr(agent, "_system_messages", [])
            if system_messages:
                system_message = system_messages[0].content
        
        self._system_prompt = dspy.Prompt(system_message or "You are a helpful assistant.")

        self._tool_prompts = []
        tools = getattr(agent, "_tools", []) or getattr(agent, "tools", [])
        for tool in tools:
            description = getattr(tool, "description", "") or ""
            self._tool_prompts.append(dspy.Prompt(description))

        # Signature is generic: user_request → answer
        class _Sig(dspy.Signature):
            """{{system_prompt}}"""
            user_request: str = dspy.InputField()
            answer: str = dspy.OutputField()

        self._predict = dspy.Predict(_Sig)

    def forward(self, user_request: str) -> Any:
        """Forward pass through the agent."""
        _check_dspy_available()
        import dspy
        
        # Patch live values into the wrapped agent
        if hasattr(self._agent, "system_message"):
            self._agent.system_message = self._system_prompt.value
        elif hasattr(self._agent, "_system_messages") and self._agent._system_messages:
            from autogen_core.models import SystemMessage
            self._agent._system_messages[0] = SystemMessage(content=self._system_prompt.value)
        
        # Update tool descriptions
        tools = getattr(self._agent, "_tools", []) or getattr(self._agent, "tools", [])
        for prompt, tool in zip(self._tool_prompts, tools):
            if hasattr(tool, "description"):
                tool.description = prompt.value

        # For now, use the predict method as a fallback
        # In a real implementation, we'd call the agent's run method
        # but that requires more complex async handling
        prediction = self._predict(user_request=user_request)
        return dspy.Prediction(answer=prediction.answer)

    # Convenient handles for back-end to read tuned texts later
    @property
    def learnable_system_prompt(self) -> Any:
        """Get the learnable system prompt."""
        return self._system_prompt

    @property
    def learnable_tool_prompts(self) -> List[Any]:
        """Get the learnable tool prompts."""
        return self._tool_prompts