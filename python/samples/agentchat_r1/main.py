import asyncio
import os
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
from autogen_core.models import ModelFamily

async def main() -> None:
    # Create model client for DeepSeek R1 hosted on Hugging Face.
    api_key = os.environ["HF_TOKEN"] # Hugging Face access token.
    model_client = OpenAIChatCompletionClient(
        model="deepseek-ai/DeepSeek-R1",
        api_key=api_key,
        base_url="https://api-inference.huggingface.co/v1/",
        model_info={
            "function_calling": False,
            "json_output": False,
            "vision": False,
            "family": ModelFamily.R1,
        }
    )

    # Create an agent that can use the model client.
    assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="Only output a single code block in your final response.",
        model_client_stream=True, # Enable streaming for the model client.
    )

    # Create code executor.
    code_executor = DockerCommandLineCodeExecutor(work_dir="coding")

    # Create an agent that can execute code.
    code_executor_agent = CodeExecutorAgent(
        name="coder",
        code_executor=code_executor,
        sources=["assistant"],
    )

    # Create a round robin group chat with the agents.
    group_chat = RoundRobinGroupChat(
        [assistant, code_executor_agent],
        max_turns=2, # Set the maximum number of turns to 2 so control can be returned to the user after the coder agent's turn.
    )

    # Start the code executor in a managed context.
    async with code_executor:
        task = "Create a plot showing the NVIDA stock price over the last 30 days."
        # Run the group chat.
        await Console(group_chat.run_stream(task=task))
        while True:
            # Ask the user if they want to continue.
            user_feedback = input("Continue? (y/n): ")
            if user_feedback.strip().lower() != "y":
                break
            # Run the group chat again.
            await Console(group_chat.run_stream(task=task))

if __name__ == "__main__":
    asyncio.run(main())