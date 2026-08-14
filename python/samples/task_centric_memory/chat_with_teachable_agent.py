from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.experimental.task_centric_memory import MemoryController
from autogen_ext.experimental.task_centric_memory.utils import Teachability


async def main():
    # Create a client
    client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06", )

    # Create an instance of Task-Centric Memory, passing minimal parameters for this simple example
    memory_controller = MemoryController(reset=False, client=client)

    # Wrap the memory controller in a Teachability instance
    teachability = Teachability(memory_controller=memory_controller)

    # Create an AssistantAgent, and attach teachability as its memory
    assistant_agent = AssistantAgent(
        name="teachable_agent",
        system_message = "You are a helpful AI assistant, with the special ability to remember user teachings from prior conversations.",
        model_client=client,
        memory=[teachability],
    )

    # Enter a loop to chat with the teachable agent
    print("Now chatting with a teachable agent. Please enter your first message. Type 'exit' or 'quit' to quit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        await Console(assistant_agent.run_stream(task=user_input))

    # Close the connection to the client
    await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
