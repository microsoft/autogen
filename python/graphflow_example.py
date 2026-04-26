"""
GraphFlow Example: Multi-Agent Workflow

This script demonstrates how to use GraphFlow (directed graph execution) for multi-agent workflows, including sequential and parallel flows.
"""
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --- Sequential Flow Example ---
async def sequential_flow():
    client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
    writer = AssistantAgent("writer", model_client=client, system_message="Draft a short paragraph on climate change.")
    reviewer = AssistantAgent("reviewer", model_client=client, system_message="Review the draft and suggest improvements.")
    builder = DiGraphBuilder()
    builder.add_node(writer).add_node(reviewer)
    builder.add_edge(writer, reviewer)
    graph = builder.build()
    flow = GraphFlow([writer, reviewer], graph=graph)
    print("\n--- Sequential Flow ---\n")
    await Console(flow.run_stream(task="Write a short paragraph about climate change."))
    await client.close()

# --- Parallel Flow with Join Example ---
async def parallel_flow():
    client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
    writer = AssistantAgent("writer", model_client=client, system_message="Draft a short paragraph on climate change.")
    editor1 = AssistantAgent("editor1", model_client=client, system_message="Edit the paragraph for grammar.")
    editor2 = AssistantAgent("editor2", model_client=client, system_message="Edit the paragraph for style.")
    final_reviewer = AssistantAgent(
        "final_reviewer",
        model_client=client,
        system_message="Consolidate the grammar and style edits into a final version.",
    )
    builder = DiGraphBuilder()
    builder.add_node(writer).add_node(editor1).add_node(editor2).add_node(final_reviewer)
    builder.add_edge(writer, editor1)
    builder.add_edge(writer, editor2)
    builder.add_edge(editor1, final_reviewer)
    builder.add_edge(editor2, final_reviewer)
    graph = builder.build()
    flow = GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
    )
    print("\n--- Parallel Flow with Join ---\n")
    await Console(flow.run_stream(task="Write a short paragraph about climate change."))
    await client.close()

if __name__ == "__main__":
    asyncio.run(sequential_flow())
    asyncio.run(parallel_flow())
