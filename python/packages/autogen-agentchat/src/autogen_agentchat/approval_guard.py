"""Approval guard for controlling execution of potentially harmful actions."""

import asyncio
import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import Any, ClassVar, Generator, List, Literal, Optional, TypedDict, cast

from autogen_core import CancellationToken, EVENT_LOGGER_NAME
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.utils import extract_json_from_str
from pydantic import BaseModel

from .guarded_action import BaseApprovalGuard, MaybeRequiresApproval
from .input_func import AsyncInputFunc, InputFuncType, SyncInputFunc
from .messages import MultiModalMessage, TextMessage


DEFAULT_REQUIRES_APPROVAL: MaybeRequiresApproval = "always"


class ApprovalResponse(BaseModel):
    """Structured response for approval decisions."""
    requires_approval: bool
    reason: str


class UserInputResponse(TypedDict):
    """Response from user input with approval decision."""
    accepted: bool
    content: str


@dataclass
class ApprovalConfig:
    """Configuration for approval policies."""
    approval_policy: Literal[
        "always", "never", "auto-conservative", "auto-permissive"
    ] = "never"


class ApprovalGuardContext:
    """Context manager for approval guard instances."""
    
    def __init__(self) -> None:
        raise RuntimeError(
            "ApprovalGuardContext cannot be instantiated. It is a static class."
        )

    _APPROVAL_GUARD_CONTEXT_VAR: ClassVar[ContextVar[BaseApprovalGuard | None]] = (
        ContextVar("_APPROVAL_GUARD_CONTEXT_VAR")
    )

    @classmethod
    @contextmanager
    def populate_context(
        cls, ctx: BaseApprovalGuard | None
    ) -> Generator[None, Any, None]:
        """Populate the approval guard context."""
        token = cls._APPROVAL_GUARD_CONTEXT_VAR.set(ctx)
        try:
            yield
        finally:
            cls._APPROVAL_GUARD_CONTEXT_VAR.reset(token)

    @classmethod
    def approval_guard(cls) -> BaseApprovalGuard | None:
        """Get the current approval guard from context."""
        try:
            return cls._APPROVAL_GUARD_CONTEXT_VAR.get()
        except LookupError as e:
            raise RuntimeError(
                "ApprovalGuardContext.approval_guard() should only be called "
                "when an approval guard is set in context."
            ) from e


ACTION_GUARD_SYSTEM_MESSAGE = """
The Approval Guard oversees every proposed action before execution.  
It detects actions that are irreversible, potentially harmful, or likely to cause real-world impact that the user would not want to happen.  

Please evaluate this action carefully considering the following criteria:
- Does the action have potential real-world consequences affecting user safety or security?
- Could the action cause irreversible changes or require complex steps to undo?
- Does the action impact data integrity, privacy, or significant system state?
- Could the action affect other users or external entities in any impactful way?

If the answer to any of the above is yes, the action should be considered harmful or impactful and require explicit user approval.

Examples for when the action should require human approval:
- If code execution involves file system modifications outside a sandbox
- If code makes network requests to external services
- If code installs or modifies system packages
- If code accesses sensitive environment variables or credentials

Examples for when the action should not require human approval:
- If code performs simple calculations or data processing
- If code only reads from provided input data
- If code generates visualizations or reports
- If code runs in a secure sandbox environment

When unsure, err on the side of caution and require human approval.

Please respond with "YES" (requires human approval) or "NO" (does not require human approval) ONLY to indicate your decision.
"""

IRREVERSIBLE_CHECK_PROMPT_TEMPLATE = """
The action proposed by the agent is:

{action_description}

Please respond with "YES" (requires human approval) or "NO" (does not require human approval) ONLY to indicate your decision.
"""

IRREVERSIBLE_CHECK_PROMPT_TEMPLATE_STRUCTURED = """
The action proposed by the agent is:

{action_description}

Please provide your decision with reasoning in the following JSON format:
{{
    "requires_approval": true/false,
    "reason": "Brief explanation for your decision"
}}
"""


class ApprovalGuard(BaseApprovalGuard):
    """Approval guard implementation for controlling action execution.
    
    The ApprovalGuard provides approval-based control over code execution in AutoGen agents.
    It supports multiple approval policies including always/never approval, and intelligent
    LLM-based approval decisions.
    
    Examples:
        Basic usage with always requiring approval:
        
        .. code-block:: python
        
            import asyncio
            from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalConfig
            from autogen_agentchat.agents import CodeExecutorAgent
            from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            
            async def my_input_func(prompt: str, cancellation_token=None) -> str:
                return input(f"{prompt}\nApprove? (yes/no): ")
            
            # Create approval guard with always approval policy
            approval_guard = ApprovalGuard(
                input_func=my_input_func,
                config=ApprovalConfig(approval_policy="always")
            )
            
            # Use with CodeExecutorAgent
            code_executor = LocalCommandLineCodeExecutor()
            agent = CodeExecutorAgent(
                name="code_executor",
                code_executor=code_executor,
                approval_guard=approval_guard
            )
            
            # Agent will now require approval for all code execution
            
        Intelligent approval with LLM:
        
        .. code-block:: python
        
            import asyncio
            from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalConfig
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            
            async def my_input_func(prompt: str, cancellation_token=None) -> str:
                return input(f"{prompt}\nApprove? (yes/no): ")
            
            # Create model client for intelligent decisions
            model_client = OpenAIChatCompletionClient(model="gpt-4o")
            
            # Create approval guard with conservative auto-approval
            approval_guard = ApprovalGuard(
                input_func=my_input_func,
                model_client=model_client,
                config=ApprovalConfig(approval_policy="auto-conservative")
            )
            
            # Guard will use LLM to determine if approval is needed
    """

    def __init__(
        self,
        input_func: Optional[InputFuncType] = None,
        default_approval: bool = True,
        model_client: Optional[ChatCompletionClient] = None,
        config: Optional[ApprovalConfig] = None,
    ):
        """Initialize the approval guard.
        
        Args:
            input_func: Function to get user input for approval decisions
            default_approval: Default approval decision when input_func is None
            model_client: Model client for intelligent approval decisions
            config: Configuration for approval policies
        """
        self.model_client = model_client
        self.input_func = input_func
        self._is_async = iscoroutinefunction(input_func) if input_func else False
        self.default_approval = default_approval
        self.config = config or ApprovalConfig()
        self.logger = logging.getLogger(f"{EVENT_LOGGER_NAME}.ApprovalGuard")

    async def _get_input(
        self, prompt: str, cancellation_token: Optional[CancellationToken]
    ) -> str:
        """Handle input based on function signature."""
        if self.input_func is None:
            raise RuntimeError("No input function provided")
            
        try:
            if self._is_async:
                async_func = cast(AsyncInputFunc, self.input_func)
                return await async_func(prompt, cancellation_token)
            else:
                sync_func = cast(SyncInputFunc, self.input_func)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, sync_func, prompt)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to get user input: {str(e)}") from e

    async def requires_approval(
        self,
        baseline: MaybeRequiresApproval,
        llm_guess: MaybeRequiresApproval,
        action_context: List[LLMMessage],
    ) -> bool:
        """Check if the action requires approval based on policy and context."""
        if self.config.approval_policy == "always":
            return True

        if self.config.approval_policy == "never":
            return False

        # Handle baseline policies
        if baseline == "never":
            return False
        elif baseline == "always":
            return True

        # Smart approval policies
        if self.config.approval_policy == "auto-permissive":
            return llm_guess != "never"
        
        # auto-conservative policy mode
        if self.model_client is None:
            return self.default_approval
            
        action_proposal = action_context[-1] if action_context else None
        if action_proposal is None:
            return self.default_approval

        system_message = SystemMessage(content=ACTION_GUARD_SYSTEM_MESSAGE)
        
        # Use recent context for decision
        selected_context = action_context[:-1]
        if len(selected_context) > 5:
            selected_context = selected_context[-5:]

        action_content = self._extract_content_string(action_proposal)

        # Try structured output first, then JSON mode, then fallback to text
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.model_client.model_info.get("structured_output", False):
                    # Use structured output with Pydantic model
                    request_messages = [
                        system_message,
                        UserMessage(
                            content=IRREVERSIBLE_CHECK_PROMPT_TEMPLATE_STRUCTURED.format(
                                action_description=action_content
                            ),
                            source="user",
                        ),
                    ]
                    result = await self.model_client.create(
                        request_messages, json_output=ApprovalResponse
                    )
                    
                    if isinstance(result.content, ApprovalResponse):
                        self.logger.info(
                            f"Structured approval check for {action_content}: {result.content.requires_approval} - {result.content.reason}"
                        )
                        return result.content.requires_approval
                    
                elif self.model_client.model_info.get("json_output", False):
                    # Use JSON mode
                    request_messages = [
                        system_message,
                        UserMessage(
                            content=IRREVERSIBLE_CHECK_PROMPT_TEMPLATE_STRUCTURED.format(
                                action_description=action_content
                            ),
                            source="user",
                        ),
                    ]
                    result = await self.model_client.create(request_messages, json_output=True)
                    
                    if isinstance(result.content, str):
                        try:
                            # Try to extract JSON from the response
                            json_objects = extract_json_from_str(result.content)
                            if json_objects:
                                json_response = json_objects[0]
                                if "requires_approval" in json_response:
                                    requires_approval = bool(json_response["requires_approval"])
                                    reason = json_response.get("reason", "No reason provided")
                                    self.logger.info(
                                        f"JSON approval check for {action_content}: {requires_approval} - {reason}"
                                    )
                                    return requires_approval
                        except (json.JSONDecodeError, ValueError, KeyError) as e:
                            self.logger.warning(f"Failed to parse JSON response on attempt {attempt + 1}: {e}")
                            if attempt == max_retries - 1:
                                # Fall through to text-based approach
                                break
                            continue
                
                # Fallback to text-based approach
                request_messages = [
                    system_message,
                    UserMessage(
                        content=IRREVERSIBLE_CHECK_PROMPT_TEMPLATE.format(
                            action_description=action_content
                        ),
                        source="user",
                    ),
                ]
                
                result = await self.model_client.create(request_messages)

                if not isinstance(result.content, str):
                    self.logger.warning(
                        "Model did not return a string response. Defaulting to True."
                    )
                    return True

                self.logger.info(
                    f"Text-based approval check for {action_content}: {result.content}"
                )

                response = result.content.strip().lower()
                if response in ["yes", "y"]:
                    return True
                elif response in ["no", "n"]:
                    return False
                else:
                    self.logger.warning(
                        f"Model returned invalid response: {result.content}. Defaulting to True."
                    )
                    return True
                    
            except Exception as e:
                self.logger.warning(f"Error on approval attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    self.logger.warning("All attempts failed. Defaulting to True.")
                    return True
                continue
        
        # Should not reach here, but return default if all attempts fail
        return True

    async def get_approval(
        self, action_description: TextMessage | MultiModalMessage
    ) -> bool:
        """Get user approval for the specified action."""
        if self.input_func is None:
            return self.default_approval

        action_description_str = self._extract_content_string(action_description)
        
        result_or_json = await self._get_input(action_description_str, None)
        result_or_json = result_or_json.strip()

        # Try to parse as JSON first
        if result_or_json.startswith("{"):
            try:
                result = json.loads(result_or_json)
                if isinstance(result, dict) and "accepted" in result:
                    return bool(result["accepted"])
            except json.JSONDecodeError:
                pass

        # Parse simple text responses
        response = result_or_json.lower()
        if response in ["accept", "yes", "y", "true", "approve"]:
            return True
        elif response in ["deny", "no", "n", "false", "reject"]:
            return False
        else:
            # Default to configured default if response is unclear
            return self.default_approval

    def _extract_content_string(self, message: any) -> str:
        """Extract string content from various message types."""
        if hasattr(message, 'content'):
            content = message.content
        else:
            content = message
            
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            content_parts = []
            for item in content:
                if isinstance(item, str):
                    content_parts.append(item)
                else:
                    try:
                        content_parts.append(json.dumps(item))
                    except (TypeError, ValueError):
                        content_parts.append(str(item))
            return "\n".join(content_parts)
        else:
            return str(content)