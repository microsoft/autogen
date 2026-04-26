"""
LangGraph-Backed Agent Example

This example demonstrates how to create an AI agent using LangGraph, integrated with the AutoGen agent runtime. The agent can use tools (e.g., get_weather) and respond to user queries.

Requirements:
- pip install langgraph langchain-openai azure-identity autogen-core autogen-ext

Run with: python python/core_langgraph_tool_use_agent_example.py
"""
import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable, List, Literal

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool  # pyright: ignore
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

# ------------------- Message Protocol -------------------
@dataclass
class Message:
    content: str

# ------------------- Tool Definition -------------------
@tool  # pyright: ignore
def get_weather(location: str) -> str:
    """Call to surf the web."""
    if "sf" in location.lower() or "san francisco" in location.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."

# ------------------- LangGraph Tool Use Agent -------------------
class LangGraphToolUseAgent(RoutedAgent):
    def __init__(self, description: str, model: ChatOpenAI, tools: List[Callable[..., Any]]) -> None:  # pyright: ignore
        super().__init__(description)
        self._model = model.bind_tools(tools)  # pyright: ignore

        def should_continue(state: MessagesState) -> Literal["tools", END]:  # type: ignore
            messages = state["messages"]
            last_message = messages[-1]
            if getattr(last_message, "tool_calls", None):  # type: ignore
                return "tools"
            return END

        async def call_model(state: MessagesState):  # type: ignore
            messages = state["messages"]
            response = await self._model.ainvoke(messages)
            return {"messages": [response]}

        tool_node = ToolNode(tools)  # pyright: ignore
        self._workflow = StateGraph(MessagesState)
        self._workflow.add_node("agent", call_model)  # pyright: ignore
        self._workflow.add_node("tools", tool_node)  # pyright: ignore
        self._workflow.set_entry_point("agent")
        self._workflow.add_conditional_edges("agent", should_continue)  # type: ignore
        self._workflow.add_edge("tools", "agent")
        self._app = self._workflow.compile()

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        final_state = await self._app.ainvoke(
            {
                "messages": [
                    SystemMessage(
                        content="You are a helpful AI assistant. You can use tools to help answer questions."
                    ),
                    HumanMessage(content=message.content),
                ]
            },
            config={"configurable": {"thread_id": 42}},
        )
        response = Message(content=final_state["messages"][-1].content)
        return response

# ------------------- Main Example -------------------
async def main():
    runtime = SingleThreadedAgentRuntime()
    await LangGraphToolUseAgent.register(
        runtime,
        "langgraph_tool_use_agent",
        lambda: LangGraphToolUseAgent(
            "Tool use agent",
            ChatOpenAI(
                model="gpt-4o",
                # api_key=os.getenv("OPENAI_API_KEY"),
            ),
            # To use Azure OpenAI, uncomment below and provide deployment details:
            # AzureChatOpenAI(
            #     azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            #     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            #     api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            #     azure_ad_token_provider=get_bearer_token_provider(DefaultAzureCredential()),
            # ),
            [get_weather],
        ),
    )
    agent = AgentId("langgraph_tool_use_agent", key="default")
    runtime.start()
    response = await runtime.send_message(Message("What's the weather in SF?"), agent)
    print(response.content)
    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
