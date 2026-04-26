"""
SelectorGroupChat Advanced Customization Example: NBA Player Analysis

This script demonstrates advanced customization of SelectorGroupChat:
- Custom selector_func for PlanningAgent to always follow specialized agents
- Custom candidate_func for dynamic candidate filtering
- UserProxyAgent for human-in-the-loop approval
- Reasoning model (o3-mini) with minimal prompt and no planning agent
"""
import asyncio
from typing import Sequence, List
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# --- Mock Tools ---
def search_web_tool(query: str) -> str:
    if "2006-2007" in query:
        return """Here are the total points scored by Miami Heat players in the 2006-2007 season:\n        Udonis Haslem: 844 points\n        Dwayne Wade: 1397 points\n        James Posey: 550 points\n        ...\n        """
    elif "2007-2008" in query:
        return "The number of total rebounds for Dwayne Wade in the Miami Heat season 2007-2008 is 214."
    elif "2008-2009" in query:
        return "The number of total rebounds for Dwayne Wade in the Miami Heat season 2008-2009 is 398."
    return "No data found."

def percentage_change_tool(start: float, end: float) -> float:
    return ((end - start) / start) * 100

# --- Model Clients ---
gpt4o_client = OpenAIChatCompletionClient(model="gpt-4o")
o3mini_client = OpenAIChatCompletionClient(model="o3-mini")

# --- Agents for GPT-4o examples ---
planning_agent = AssistantAgent(
    "PlanningAgent",
    description="An agent for planning tasks, this agent should be the first to engage when given a new task.",
    model_client=gpt4o_client,
    system_message="""
    You are a planning agent.
    Your job is to break down complex tasks into smaller, manageable subtasks.
    Your team members are:
        WebSearchAgent: Searches for information
        DataAnalystAgent: Performs calculations

    You only plan and delegate tasks - you do not execute them yourself.

    When assigning tasks, use this format:
    1. <agent> : <task>

    After all tasks are complete, summarize the findings and end with \"TERMINATE\".
    """,
)

web_search_agent = AssistantAgent(
    "WebSearchAgent",
    description="An agent for searching information on the web.",
    tools=[search_web_tool],
    model_client=gpt4o_client,
    system_message="""
    You are a web search agent.
    Your only tool is search_tool - use it to find information.
    You make only one search call at a time.
    Once you have the results, you never do calculations based on them.
    """,
)

data_analyst_agent = AssistantAgent(
    "DataAnalystAgent",
    description="An agent for performing calculations.",
    model_client=gpt4o_client,
    tools=[percentage_change_tool],
    system_message="""
    You are a data analyst.
    Given the tasks you have been assigned, you should analyze the data and provide results using the tools provided.
    If you have not seen the data, ask for it.
    """,
)

user_proxy_agent = UserProxyAgent(
    "UserProxyAgent",
    description="A proxy for the user to approve or disapprove tasks.",
)

# --- Termination Conditions ---
text_mention_termination = TextMentionTermination("TERMINATE")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination = text_mention_termination | max_messages_termination

# --- Selector Prompt ---
selector_prompt = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""

task = "Who was the Miami Heat player with the highest points in the 2006-2007 season, and what was the percentage change in his total rebounds between the 2007-2008 and 2008-2009 seasons?"

# --- Custom Selector Function Example ---
def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    if messages[-1].source != planning_agent.name:
        return planning_agent.name
    return None

# --- Custom Candidate Function Example ---
def candidate_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str]:
    if messages[-1].source == "user":
        return [planning_agent.name]
    last_message = messages[-1]
    if last_message.source == planning_agent.name:
        participants = []
        if web_search_agent.name in last_message.to_text():
            participants.append(web_search_agent.name)
        if data_analyst_agent.name in last_message.to_text():
            participants.append(data_analyst_agent.name)
        if participants:
            return participants
    previous_set_of_agents = set(message.source for message in messages)
    if web_search_agent.name in previous_set_of_agents and data_analyst_agent.name in previous_set_of_agents:
        return [planning_agent.name]
    return [planning_agent.name, web_search_agent.name, data_analyst_agent.name]

# --- Selector Function with UserProxyAgent Example ---
def selector_func_with_user_proxy(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    if messages[-1].source != planning_agent.name and messages[-1].source != user_proxy_agent.name:
        return planning_agent.name
    if messages[-1].source == planning_agent.name:
        if len(messages) > 1 and messages[-2].source == user_proxy_agent.name and "APPROVE" in messages[-1].content.upper():
            return None
        return user_proxy_agent.name
    if messages[-1].source == user_proxy_agent.name:
        if "APPROVE" not in messages[-1].content.upper():
            return planning_agent.name
    return None

# --- Reasoning Model Example (no planning agent, minimal prompt) ---
def run_reasoning_model():
    web_search_agent_r = AssistantAgent(
        "WebSearchAgent",
        description="An agent for searching information on the web.",
        tools=[search_web_tool],
        model_client=o3mini_client,
        system_message="Use web search tool to find information.",
    )
    data_analyst_agent_r = AssistantAgent(
        "DataAnalystAgent",
        description="An agent for performing calculations.",
        model_client=o3mini_client,
        tools=[percentage_change_tool],
        system_message="Use tool to perform calculation. If you have not seen the data, ask for it.",
    )
    user_proxy_agent_r = UserProxyAgent(
        "UserProxyAgent",
        description="A user to approve or disapprove tasks.",
    )
    selector_prompt_r = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
When the task is complete, let the user approve or disapprove the task.
"""
    team = SelectorGroupChat(
        [web_search_agent_r, data_analyst_agent_r, user_proxy_agent_r],
        model_client=o3mini_client,
        termination_condition=termination,
        selector_prompt=selector_prompt_r,
        allow_repeated_speaker=True,
    )
    asyncio.run(Console(team.run_stream(task=task)))

if __name__ == "__main__":
    print("\n--- Running with custom selector_func ---\n")
    team = SelectorGroupChat(
        [planning_agent, web_search_agent, data_analyst_agent],
        model_client=gpt4o_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True,
        selector_func=selector_func,
    )
    asyncio.run(team.reset())
    asyncio.run(Console(team.run_stream(task=task)))

    print("\n--- Running with custom candidate_func ---\n")
    team = SelectorGroupChat(
        [planning_agent, web_search_agent, data_analyst_agent],
        model_client=gpt4o_client,
        termination_condition=termination,
        candidate_func=candidate_func,
    )
    asyncio.run(team.reset())
    asyncio.run(Console(team.run_stream(task=task)))

    print("\n--- Running with UserProxyAgent and selector_func ---\n")
    team = SelectorGroupChat(
        [planning_agent, web_search_agent, data_analyst_agent, user_proxy_agent],
        model_client=gpt4o_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
        selector_func=selector_func_with_user_proxy,
        allow_repeated_speaker=True,
    )
    asyncio.run(team.reset())
    asyncio.run(Console(team.run_stream(task=task)))

    print("\n--- Running with reasoning model (o3-mini), no planning agent ---\n")
    run_reasoning_model()
