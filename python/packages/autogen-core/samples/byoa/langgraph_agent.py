"""
This example demonstrates how to create an AI agent using LangGraph.
Based on the example in the LangGraph documentation:
https://langchain-ai.github.io/langgraph/
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, List, Literal

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext
from autogen_core.components import RoutedAgent, message_handler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool  # pyright: ignore
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


@dataclass
class Message:
    content: str


# Define the tools for the agent to use
@tool  # pyright: ignore
def get_weather(location: str) -> str:
    """Call to surf the web."""
    # This is a placeholder, but don't tell the LLM that...
    if "sf" in location.lower() or "san francisco" in location.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


# Define the tool-use agent using LangGraph.
class LangGraphToolUseAgent(RoutedAgent):
    def __init__(self, description: str, model: ChatOpenAI, tools: List[Callable[..., Any]]) -> None:  # pyright: ignore
        super().__init__(description)
        self._model = model.bind_tools(tools)  # pyright: ignore

        # Define the function that determines whether to continue or not
        def should_continue(state: MessagesState) -> Literal["tools", END]:  # type: ignore
            messages = state["messages"]
            last_message = messages[-1]
            # If the LLM makes a tool call, then we route to the "tools" node
            if last_message.tool_calls:  # type: ignore
                return "tools"
            # Otherwise, we stop (reply to the user)
            return END

        # Define the function that calls the model
        async def call_model(state: MessagesState):  # type: ignore
            messages = state["messages"]
            response = await self._model.ainvoke(messages)
            # We return a list, because this will get added to the existing list
            return {"messages": [response]}

        tool_node = ToolNode(tools)  # pyright: ignore

        # Define a new graph
        self._workflow = StateGraph(MessagesState)

        # Define the two nodes we will cycle between
        self._workflow.add_node("agent", call_model)  # pyright: ignore
        self._workflow.add_node("tools", tool_node)  # pyright: ignore

        # Set the entrypoint as `agent`
        # This means that this node is the first one called
        self._workflow.set_entry_point("agent")

        # We now add a conditional edge
        self._workflow.add_conditional_edges(
            # First, we define the start node. We use `agent`.
            # This means these are the edges taken after the `agent` node is called.
            "agent",
            # Next, we pass in the function that will determine which node is called next.
            should_continue,  # type: ignore
        )

        # We now add a normal edge from `tools` to `agent`.
        # This means that after `tools` is called, `agent` node is called next.
        self._workflow.add_edge("tools", "agent")

        # Finally, we compile it!
        # This compiles it into a LangChain Runnable,
        # meaning you can use it as you would any other runnable.
        # Note that we're (optionally) passing the memory when compiling the graph
        self._app = self._workflow.compile()

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        # Use the Runnable
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


async def main() -> None:
    # Create runtime.
    runtime = SingleThreadedAgentRuntime()
    # Register the agent.
    await runtime.register(
        "langgraph_tool_use_agent",
        lambda: LangGraphToolUseAgent(
            "Tool use agent",
            ChatOpenAI(model="gpt-4o-mini"),
            [get_weather],
        ),
    )
    agent = AgentId("langgraph_tool_use_agent", key="default")
    # Start the runtime.
    runtime.start()
    # Send a message to the agent and get a response.
    response = await runtime.send_message(Message("What's the weather in SF?"), agent)
    print(response.content)
    # Stop the runtime.
    await runtime.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
