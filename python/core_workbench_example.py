"""
core_workbench_example.py

Demonstrates using a Workbench and MCP Workbench in AutoGen:
- WorkbenchAgent that loops over tool calls and results
- Integration with model client, model context, and workbench
- (Optional) MCP Workbench for remote tool orchestration

To run:
    python core_workbench_example.py

Note: Requires OPENAI_API_KEY in environment for OpenAI examples.
      For MCP Workbench, ensure MCP server is running and autogen-ext[mcp] is installed.
"""
import asyncio
import json
from dataclasses import dataclass
from typing import List

try:
    from autogen_core import (
        FunctionCall, MessageContext, RoutedAgent, message_handler, AgentId, SingleThreadedAgentRuntime
    )
    from autogen_core.model_context import BufferedChatCompletionContext, ChatCompletionContext
    from autogen_core.models import (
        AssistantMessage, ChatCompletionClient, FunctionExecutionResult, FunctionExecutionResultMessage, LLMMessage, SystemMessage, UserMessage
    )
    from autogen_core.tools import ToolResult, Workbench
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    # For MCP Workbench (optional)
    from autogen_ext.tools.mcp import McpWorkbench, SseServerParams
except ImportError as e:
    print("Required packages not installed:", e)
    print("Please install autogen-core, autogen-ext, and mcp dependencies if using MCP Workbench.")
    exit(1)

@dataclass
class Message:
    content: str

class WorkbenchAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, model_context: ChatCompletionContext, workbench: Workbench) -> None:
        super().__init__("An agent with a workbench")
        self._system_messages: List[LLMMessage] = [SystemMessage(content="You are a helpful AI assistant.")]
        self._model_client = model_client
        self._model_context = model_context
        self._workbench = workbench

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        await self._model_context.add_message(UserMessage(content=message.content, source="user"))
        print("---------User Message-----------")
        print(message.content)
        create_result = await self._model_client.create(
            messages=self._system_messages + (await self._model_context.get_messages()),
            tools=(await self._workbench.list_tools()),
            cancellation_token=ctx.cancellation_token,
        )
        while isinstance(create_result.content, list) and all(isinstance(call, FunctionCall) for call in create_result.content):
            print("---------Function Calls-----------")
            for call in create_result.content:
                print(call)
            await self._model_context.add_message(AssistantMessage(content=create_result.content, source="assistant"))
            print("---------Function Call Results-----------")
            results: List[ToolResult] = []
            for call in create_result.content:
                result = await self._workbench.call_tool(
                    call.name, arguments=json.loads(call.arguments), cancellation_token=ctx.cancellation_token
                )
                results.append(result)
                print(result)
            await self._model_context.add_message(
                FunctionExecutionResultMessage(
                    content=[
                        FunctionExecutionResult(
                            call_id=call.id,
                            content=result.to_text(),
                            is_error=result.is_error,
                            name=result.name,
                        )
                        for call, result in zip(create_result.content, results, strict=False)
                    ]
                )
            )
            create_result = await self._model_client.create(
                messages=self._system_messages + (await self._model_context.get_messages()),
                tools=(await self._workbench.list_tools()),
                cancellation_token=ctx.cancellation_token,
            )
        assert isinstance(create_result.content, str)
        print("---------Final Response-----------")
        print(create_result.content)
        await self._model_context.add_message(AssistantMessage(content=create_result.content, source="assistant"))
        return Message(content=create_result.content)

async def main():
    # Example: Using MCP Workbench (requires MCP server running)
    # Uncomment and configure the following block to use MCP Workbench
    # playwright_server_params = SseServerParams(url="http://localhost:8931/sse")
    # async with McpWorkbench(playwright_server_params) as workbench:
    #     runtime = SingleThreadedAgentRuntime()
    #     await WorkbenchAgent.register(
    #         runtime=runtime,
    #         type="WebAgent",
    #         factory=lambda: WorkbenchAgent(
    #             model_client=OpenAIChatCompletionClient(model="gpt-4.1-nano"),
    #             model_context=BufferedChatCompletionContext(buffer_size=10),
    #             workbench=workbench,
    #         ),
    #     )
    #     runtime.start()
    #     await runtime.send_message(
    #         Message(content="Use Bing to find out the address of Microsoft Building 99"),
    #         recipient=AgentId("WebAgent", "default"),
    #     )
    #     await runtime.stop()

    # Example: Using a local Workbench (with no tools, for demonstration)
    class DummyWorkbench(Workbench):
        async def list_tools(self):
            return []
        async def call_tool(self, name, arguments, cancellation_token):
            return ToolResult(name=name, result="No tool available", is_error=True)
    workbench = DummyWorkbench()
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    model_context = BufferedChatCompletionContext(buffer_size=5)
    runtime = SingleThreadedAgentRuntime()
    await WorkbenchAgent.register(
        runtime=runtime,
        type="WorkbenchAgent",
        factory=lambda: WorkbenchAgent(
            model_client=model_client,
            model_context=model_context,
            workbench=workbench,
        ),
    )
    runtime.start()
    agent_id = AgentId("WorkbenchAgent", "default")
    message = Message("What is the weather in Seattle today?")
    response = await runtime.send_message(message, agent_id)
    print("Agent response:", response.content)
    await runtime.stop()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
