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
        # Initialize basic attributes expected by DSPy
        self.history = []

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
    
    def basic_request(self, messages: List[Dict[str, str]], **kw: Any) -> str:
        """DSPy interface method."""
        return self(messages, **kw)


# --------------------------------------------------------------------- #
# 2.  DSPy module wrapper around an existing Agent
# --------------------------------------------------------------------- #
class DSPyAgentWrapper:
    """
    Exposes `agent.system_message` and each tool description as learnable prompts.
    This is a DSPy Module that wraps an AutoGen agent.
    """

    def __init__(self, agent: Any) -> None:
        _check_dspy_available()
        import dspy
        
        self._agent = agent

        # Turn system prompt & each tool description into learnable strings
        system_message = self._get_system_message(agent)
        self._system_prompt = dspy.Prompt(system_message or "You are a helpful assistant.")

        self._tool_prompts = []
        tools = self._get_tools(agent)
        for tool in tools:
            description = getattr(tool, "description", "") or ""
            self._tool_prompts.append(dspy.Prompt(description))

        # Make this a proper DSPy Module by adding the predict component
        class AgentSignature(dspy.Signature):
            """Agent signature for processing user requests."""
            user_request: str = dspy.InputField()
            answer: str = dspy.OutputField()

        self._predict = dspy.Predict(AgentSignature)

    def _get_system_message(self, agent: Any) -> str | None:
        """Extract system message from agent."""
        # Try different ways agents might store system messages
        if hasattr(agent, "system_message"):
            return agent.system_message
        elif hasattr(agent, "_system_messages") and agent._system_messages:
            return agent._system_messages[0].content
        return None

    def _get_tools(self, agent: Any) -> List[Any]:
        """Extract tools from agent."""
        return getattr(agent, "_tools", []) or getattr(agent, "tools", [])

    def forward(self, user_request: str) -> Any:
        """Forward pass through the agent.
        
        In a full implementation, this would:
        1. Update the agent with optimized prompts
        2. Call the agent's run method 
        3. Return the result
        
        For now, we use a simple predict as a placeholder.
        """
        _check_dspy_available()
        import dspy
        
        # Patch live values into the wrapped agent
        self._update_agent_prompts()
        
        # In an ideal implementation, we'd call:
        # result = await self._agent.run(task=user_request)
        # But this requires proper async handling and depends on the agent interface
        
        # For now, use DSPy predict as a fallback
        prediction = self._predict(user_request=user_request)
        return dspy.Prediction(answer=prediction.answer)

    def _update_agent_prompts(self) -> None:
        """Update the agent with current prompt values."""
        # Update system message
        if hasattr(self._agent, "system_message"):
            self._agent.system_message = self._system_prompt.value
        elif hasattr(self._agent, "_system_messages") and self._agent._system_messages:
            from autogen_core.models import SystemMessage
            self._agent._system_messages[0] = SystemMessage(content=self._system_prompt.value)
        
        # Update tool descriptions
        tools = self._get_tools(self._agent)
        for prompt, tool in zip(self._tool_prompts, tools):
            if hasattr(tool, "description"):
                tool.description = prompt.value

    # Convenient handles for back-end to read tuned texts later
    @property
    def learnable_system_prompt(self) -> Any:
        """Get the learnable system prompt."""
        return self._system_prompt

    @property
    def learnable_tool_prompts(self) -> List[Any]:
        """Get the learnable tool prompts."""
        return self._tool_prompts