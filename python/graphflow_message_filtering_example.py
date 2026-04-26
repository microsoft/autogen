"""
GraphFlow Message Filtering Example: Multi-Agent Workflow with Message Graph

This script demonstrates message filtering in GraphFlow using MessageFilterAgent, MessageFilterConfig, and PerSourceFilter.
Includes both a simple sequential flow and an advanced conditional loop with filtered summary.
"""
import asyncio
from autogen_agentchat.agents import AssistantAgent, MessageFilterAgent, MessageFilterConfig, PerSourceFilter
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --- Simple Message Filtering Example ---
async def simple_message_filtering():
    client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
    researcher = AssistantAgent(
        "researcher", model_client=client, system_message="Summarize key facts about climate change."
    )
    analyst = AssistantAgent("analyst", model_client=client, system_message="Review the summary and suggest improvements.")
    presenter = AssistantAgent(
        "presenter", model_client=client, system_message="Prepare a presentation slide based on the final summary."
    )
    filtered_analyst = MessageFilterAgent(
        name="analyst",
        wrapped_agent=analyst,
        filter=MessageFilterConfig(per_source=[PerSourceFilter(source="researcher", position="last", count=1)]),
    )
    filtered_presenter = MessageFilterAgent(
        name="presenter",
        wrapped_agent=presenter,
        filter=MessageFilterConfig(per_source=[PerSourceFilter(source="analyst", position="last", count=1)]),
    )
    builder = DiGraphBuilder()
    builder.add_node(researcher).add_node(filtered_analyst).add_node(filtered_presenter)
    builder.add_edge(researcher, filtered_analyst).add_edge(filtered_analyst, filtered_presenter)
    flow = GraphFlow(
        participants=builder.get_participants(),
        graph=builder.build(),
    )
    print("\n--- Simple Message Filtering ---\n")
    await Console(flow.run_stream(task="Summarize key facts about climate change."))
    await client.close()

# --- Advanced Conditional Loop + Filtered Summary Example ---
async def advanced_message_filtering():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    generator = AssistantAgent("generator", model_client=model_client, system_message="Generate a list of creative ideas.")
    reviewer = AssistantAgent(
        "reviewer",
        model_client=model_client,
        system_message="Review ideas and provide feedbacks, or just 'APPROVE' for final approval.",
    )
    summarizer_core = AssistantAgent(
        "summary", model_client=model_client, system_message="Summarize the user request and the final feedback."
    )
    filtered_summarizer = MessageFilterAgent(
        name="summary",
        wrapped_agent=summarizer_core,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="reviewer", position="last", count=1),
            ]
        ),
    )
    builder = DiGraphBuilder()
    builder.add_node(generator).add_node(reviewer).add_node(filtered_summarizer)
    builder.add_edge(generator, reviewer)
    builder.add_edge(reviewer, filtered_summarizer, condition=lambda msg: "APPROVE" in msg.to_model_text())
    builder.add_edge(reviewer, generator, condition=lambda msg: "APPROVE" not in msg.to_model_text())
    builder.set_entry_point(generator)
    graph = builder.build()
    termination_condition = MaxMessageTermination(10)
    flow = GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
        termination_condition=termination_condition
    )
    print("\n--- Advanced Conditional Loop + Filtered Summary ---\n")
    await Console(flow.run_stream(task="Brainstorm ways to reduce plastic waste."))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(simple_message_filtering())
    asyncio.run(advanced_message_filtering())
