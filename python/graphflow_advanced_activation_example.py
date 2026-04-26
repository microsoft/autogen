"""
GraphFlow Advanced Cycles & Activation Groups Example

This script demonstrates advanced GraphFlow usage with cycles, activation groups, and mixed activation conditions.
Includes:
- Example 1: Loop with multiple paths and 'all' activation
- Example 2: Parallel fan-in with 'any' activation
- Example 3: Mixed activation groups (all/any)
"""
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def example1_all_activation():
    client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    agent_a = AssistantAgent("A", model_client=client, system_message="Start the process and provide initial input.")
    agent_b = AssistantAgent(
        "B",
        model_client=client,
        system_message="Process input from A or feedback from C. Say 'CONTINUE' if it's from A or 'STOP' if it's from C.",
    )
    agent_c = AssistantAgent("C", model_client=client, system_message="Review B's output and provide feedback.")
    agent_e = AssistantAgent("E", model_client=client, system_message="Finalize the process.")
    builder = DiGraphBuilder()
    builder.add_node(agent_a).add_node(agent_b).add_node(agent_c).add_node(agent_e)
    builder.add_edge(agent_a, agent_b, activation_group="initial")
    builder.add_edge(agent_b, agent_c, condition="CONTINUE")
    builder.add_edge(agent_c, agent_b, activation_group="feedback")
    builder.add_edge(agent_b, agent_e, condition="STOP")
    termination_condition = MaxMessageTermination(10)
    graph = builder.build()
    flow = GraphFlow(participants=[agent_a, agent_b, agent_c, agent_e], graph=graph, termination_condition=termination_condition)
    print("\n=== Example 1: A→B→C→B with 'All' Activation ===\n")
    await Console(flow.run_stream(task="Start a review process for a document."))
    await client.close()

async def example2_any_activation():
    client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    agent_a2 = AssistantAgent("A", model_client=client, system_message="Initiate a task that needs parallel processing.")
    agent_b2 = AssistantAgent(
        "B",
        model_client=client,
        system_message="Coordinate parallel tasks. Say 'PROCESS' to start parallel work or 'DONE' to finish.",
    )
    agent_c1 = AssistantAgent("C1", model_client=client, system_message="Handle task type 1. Say 'C1_COMPLETE' when done.")
    agent_c2 = AssistantAgent("C2", model_client=client, system_message="Handle task type 2. Say 'C2_COMPLETE' when done.")
    agent_e = AssistantAgent("E", model_client=client, system_message="Finalize the process.")
    builder2 = DiGraphBuilder()
    builder2.add_node(agent_a2).add_node(agent_b2).add_node(agent_c1).add_node(agent_c2).add_node(agent_e)
    builder2.add_edge(agent_a2, agent_b2)
    builder2.add_edge(agent_b2, agent_c1, condition="PROCESS")
    builder2.add_edge(agent_b2, agent_c2, condition="PROCESS")
    builder2.add_edge(agent_b2, agent_e, condition=lambda msg: "DONE" in msg.to_model_text())
    builder2.add_edge(
        agent_c1, agent_b2, activation_group="loop_back_group", activation_condition="any", condition="C1_COMPLETE"
    )
    builder2.add_edge(
        agent_c2, agent_b2, activation_group="loop_back_group", activation_condition="any", condition="C2_COMPLETE"
    )
    graph2 = builder2.build()
    flow2 = GraphFlow(participants=[agent_a2, agent_b2, agent_c1, agent_c2, agent_e], graph=graph2)
    print("\n=== Example 2: A→B→(C1,C2)→B with 'Any' Activation ===\n")
    await Console(flow2.run_stream(task="Start a parallel processing task."))
    await client.close()

async def example3_mixed_activation():
    client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    agent_a3 = AssistantAgent("A", model_client=client, system_message="Provide critical input that must be processed.")
    agent_b3 = AssistantAgent("B", model_client=client, system_message="Provide secondary critical input.")
    agent_c3 = AssistantAgent("C", model_client=client, system_message="Provide optional quick input.")
    agent_d3 = AssistantAgent("D", model_client=client, system_message="Process inputs based on different priority levels.")
    builder3 = DiGraphBuilder()
    builder3.add_node(agent_a3).add_node(agent_b3).add_node(agent_c3).add_node(agent_d3)
    builder3.add_edge(agent_a3, agent_d3, activation_group="critical", activation_condition="all")
    builder3.add_edge(agent_b3, agent_d3, activation_group="critical", activation_condition="all")
    builder3.add_edge(agent_c3, agent_d3, activation_group="optional", activation_condition="any")
    graph3 = builder3.build()
    flow3 = GraphFlow(participants=[agent_a3, agent_b3, agent_c3, agent_d3], graph=graph3)
    print("\n=== Example 3: Mixed Activation Groups ===\n")
    print("D will execute when:")
    print("- BOTH A AND B complete (critical group with 'all' activation), OR")
    print("- C completes (optional group with 'any' activation)")
    print("This allows for both required dependencies and fast-path triggers.\n")
    await Console(flow3.run_stream(task="Process inputs with mixed priority levels."))
    await client.close()

if __name__ == "__main__":
    asyncio.run(example1_all_activation())
    asyncio.run(example2_any_activation())
    asyncio.run(example3_mixed_activation())
