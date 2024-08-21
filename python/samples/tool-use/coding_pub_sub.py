"""
This example shows how to use pub/sub to implement
a simple interaction between a tool executor agent and a tool use agent.
1. The tool use agent receives a user message, and makes an inference using a model.
If the response is a list of function calls, the agent publishes the function calls
to the tool executor agent.
2. The tool executor agent receives the function calls, executes the tools, and publishes
the results back to the tool use agent.
3. The tool use agent receives the tool results, and makes an inference using the model again.
4. The process continues until the inference response is not a list of function calls.
5. The tool use agent publishes a final response to the user.
"""

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import FunctionCall, TypeRoutedAgent, message_handler
from agnext.components._type_subscription import TypeSubscription
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from agnext.components.tools import PythonCodeExecutionTool, Tool
from agnext.core import TopicId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agnext.core import MessageContext
from common.utils import get_chat_completion_client_from_envs


@dataclass
class ToolExecutionTask:
    session_id: str
    function_call: FunctionCall


@dataclass
class ToolExecutionTaskResult:
    session_id: str
    result: FunctionExecutionResult


@dataclass
class UserRequest:
    content: str


@dataclass
class AgentResponse:
    content: str


class ToolExecutorAgent(TypeRoutedAgent):
    """An agent that executes tools."""

    def __init__(self, description: str, tools: List[Tool]) -> None:
        super().__init__(description)
        self._tools = tools

    @message_handler
    async def handle_tool_call(self, message: ToolExecutionTask, ctx: MessageContext) -> None:
        """Handle a tool execution task. This method executes the tool and publishes the result."""
        # Find the tool
        tool = next((tool for tool in self._tools if tool.name == message.function_call.name), None)
        if tool is None:
            result_as_str = f"Error: Tool not found: {message.function_call.name}"
        else:
            try:
                arguments = json.loads(message.function_call.arguments)
                result = await tool.run_json(args=arguments, cancellation_token=ctx.cancellation_token)
                result_as_str = tool.return_value_as_string(result)
            except json.JSONDecodeError:
                result_as_str = f"Error: Invalid arguments: {message.function_call.arguments}"
            except Exception as e:
                result_as_str = f"Error: {e}"
        task_result = ToolExecutionTaskResult(
            session_id=message.session_id,
            result=FunctionExecutionResult(content=result_as_str, call_id=message.function_call.id),
        )
        assert ctx.topic_id is not None
        await self.publish_message(task_result, topic_id=ctx.topic_id)


class ToolUseAgent(TypeRoutedAgent):
    """An agent that uses tools to perform tasks. It doesn't execute the tools
    by itself, but delegates the execution to ToolExecutorAgent using pub/sub
    mechanism."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        tools: List[Tool],
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._tools = tools
        self._sessions: Dict[str, List[LLMMessage]] = {}
        self._tool_results: Dict[str, List[ToolExecutionTaskResult]] = {}
        self._tool_counter: Dict[str, int] = {}

    @message_handler
    async def handle_user_message(self, message: UserRequest, ctx: MessageContext) -> None:
        """Handle a user message. This method calls the model. If the model response is a string,
        it publishes the response. If the model response is a list of function calls, it publishes
        the function calls to the tool executor agent."""
        session_id = str(uuid.uuid4())
        self._sessions.setdefault(session_id, []).append(UserMessage(content=message.content, source="User"))
        response = await self._model_client.create(
            self._system_messages + self._sessions[session_id], tools=self._tools
        )
        self._sessions[session_id].append(AssistantMessage(content=response.content, source=self.metadata["type"]))

        if isinstance(response.content, str):
            # If the response is a string, just publish the response.
            response_message = AgentResponse(content=response.content)
            assert ctx.topic_id is not None
            await self.publish_message(response_message, topic_id=ctx.topic_id)
            print(f"AI Response: {response.content}")
            return

        # Handle the response as a list of function calls.
        assert isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content)
        self._tool_results.setdefault(session_id, [])
        self._tool_counter.setdefault(session_id, 0)

        # Publish the function calls to the tool executor agent.
        for function_call in response.content:
            task = ToolExecutionTask(session_id=session_id, function_call=function_call)
            self._tool_counter[session_id] += 1
            assert ctx.topic_id is not None
            await self.publish_message(task, topic_id=ctx.topic_id)

    @message_handler
    async def handle_tool_result(self, message: ToolExecutionTaskResult, ctx: MessageContext) -> None:
        """Handle a tool execution result. This method aggregates the tool results and
        calls the model again to get another response. If the response is a string, it
        publishes the response. If the response is a list of function calls, it publishes
        the function calls to the tool executor agent."""
        self._tool_results[message.session_id].append(message)
        self._tool_counter[message.session_id] -= 1
        if self._tool_counter[message.session_id] > 0:
            # Not all tools have finished execution.
            return
        # All tools have finished execution.
        # Aggregate tool results into a single LLM message.
        result = FunctionExecutionResultMessage(content=[r.result for r in self._tool_results[message.session_id]])
        # Clear the tool results.
        self._tool_results[message.session_id].clear()
        # Get another response from the model.
        self._sessions[message.session_id].append(result)
        response = await self._model_client.create(
            self._system_messages + self._sessions[message.session_id], tools=self._tools
        )
        self._sessions[message.session_id].append(
            AssistantMessage(content=response.content, source=self.metadata["type"])
        )
        assert ctx.topic_id is not None
        # If the response is a string, just publish the response.
        if isinstance(response.content, str):
            response_message = AgentResponse(content=response.content)
            await self.publish_message(response_message, topic_id=ctx.topic_id)
            self._tool_results.pop(message.session_id)
            self._tool_counter.pop(message.session_id)
            print(f"AI Response: {response.content}")
            return
        # Handle the response as a list of function calls.
        assert isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content)
        # Publish the function calls to the tool executor agent.
        for function_call in response.content:
            task = ToolExecutionTask(session_id=message.session_id, function_call=function_call)
            self._tool_counter[message.session_id] += 1
            await self.publish_message(task, topic_id=ctx.topic_id)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    # Define the tools.
    tools: List[Tool] = [
        PythonCodeExecutionTool(
            LocalCommandLineCodeExecutor(),
        )
    ]
    # Register agents.
    await runtime.register("tool_executor", lambda: ToolExecutorAgent("Tool Executor", tools))
    await runtime.add_subscription(TypeSubscription("default", "tool_executor"))
    await runtime.register(
        "tool_use_agent",
        lambda: ToolUseAgent(
            description="Tool Use Agent",
            system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            tools=tools,
        ),
    )
    await runtime.add_subscription(TypeSubscription("default", "tool_use_agent"))

    runtime.start()

    # Publish a task.
    await runtime.publish_message(
        UserRequest("Run the following Python code: print('Hello, World!')"), topic_id=TopicId("default", "default")
    )

    await runtime.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
