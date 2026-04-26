"""
Magentic-One Example: Multi-Agent Orchestration

This script demonstrates how to use Magentic-OneGroupChat and the MagenticOne helper class for open-ended multi-agent tasks.
"""
import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console

# --- Minimal MagenticOneGroupChat Example ---
async def magentic_one_minimal():
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    assistant = AssistantAgent(
        "Assistant",
        model_client=model_client,
    )
    team = MagenticOneGroupChat([assistant], model_client=model_client)
    await Console(team.run_stream(task="Provide a different proof for Fermat's Last Theorem"))
    await model_client.close()

# --- Magentic-One Agents Example ---
async def magentic_one_agents():
    from autogen_ext.agents.web_surfer import MultimodalWebSurfer
    # from autogen_ext.agents.file_surfer import FileSurfer
    # from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
    # from autogen_agentchat.agents import CodeExecutorAgent
    # from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    surfer = MultimodalWebSurfer(
        "WebSurfer",
        model_client=model_client,
    )
    team = MagenticOneGroupChat([surfer], model_client=model_client)
    await Console(team.run_stream(task="What is the UV index in Melbourne today?"))
    await model_client.close()

# --- MagenticOne Helper Example (with approval) ---
async def magentic_one_helper():
    from autogen_ext.teams.magentic_one import MagenticOne
    from autogen_agentchat.agents import ApprovalRequest, ApprovalResponse

    def approval_func(request: ApprovalRequest) -> ApprovalResponse:
        print(f"Code to execute:\n{request.code}")
        user_input = input("Do you approve this code execution? (y/n): ").strip().lower()
        if user_input == 'y':
            return ApprovalResponse(approved=True, reason="User approved the code execution")
        else:
            return ApprovalResponse(approved=False, reason="User denied the code execution")

    client = OpenAIChatCompletionClient(model="gpt-4o")
    m1 = MagenticOne(client=client, approval_func=approval_func)
    task = "Write a Python script to fetch data from an API."
    result = await Console(m1.run_stream(task=task))
    print(result)
    await client.close()

if __name__ == "__main__":
    print("\n--- MagenticOneGroupChat minimal example ---\n")
    asyncio.run(magentic_one_minimal())
    print("\n--- MagenticOneGroupChat with WebSurfer agent ---\n")
    asyncio.run(magentic_one_agents())
    print("\n--- MagenticOne helper class with approval ---\n")
    asyncio.run(magentic_one_helper())
