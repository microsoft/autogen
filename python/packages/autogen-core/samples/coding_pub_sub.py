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
import uuid
from dataclasses import dataclass
from typing import Dict, List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import MessageContext
from autogen_core.components import DefaultSubscription, DefaultTopicId, FunctionCall, RoutedAgent, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tools import PythonCodeExecutionTool, Tool
from autogen_ext.code_executors import DockerCommandLineCodeExecutor
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


class ToolExecutorAgent(RoutedAgent):
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
        await self.publish_message(task_result, topic_id=DefaultTopicId())


class ToolUseAgent(RoutedAgent):
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
            await self.publish_message(response_message, topic_id=DefaultTopicId())
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
            await self.publish_message(task, topic_id=DefaultTopicId())

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
        # If the response is a string, just publish the response.
        if isinstance(response.content, str):
            response_message = AgentResponse(content=response.content)
            await self.publish_message(response_message, topic_id=DefaultTopicId())
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
            await self.publish_message(task, topic_id=DefaultTopicId())


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    async with DockerCommandLineCodeExecutor() as executor:
        # Define the tools.
        tools: List[Tool] = [
            PythonCodeExecutionTool(
                executor=executor,
            )
        ]
        # Register agents.
        await runtime.register(
            "tool_executor", lambda: ToolExecutorAgent("Tool Executor", tools), lambda: [DefaultSubscription()]
        )
        await runtime.register(
            "tool_use_agent",
            lambda: ToolUseAgent(
                description="Tool Use Agent",
                system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
                model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
                tools=tools,
            ),
            lambda: [DefaultSubscription()],
        )

        runtime.start()

        # Publish a task.
        await runtime.publish_message(
            UserRequest("Run the following Python code: print('Hello, World!')"), topic_id=DefaultTopicId()
        )

        await runtime.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
