import asyncio
import os

from autogen.experimental import AssistantAgent, OpenAI, TwoAgentChat
from autogen.experimental.agents.function_calling_agent import FunctionCallingAgent
from autogen.experimental.drivers import run_in_terminal


def get_weather(city: str) -> str:
    return f"The weather in {city} is 75 degrees Fahrenheit."


async def main() -> None:
    model_client = OpenAI(model="gpt-4-turbo", api_key=os.environ["OPENAI_API_KEY"])

    assistant = AssistantAgent(
        name="agent",
        system_message="""You are a helpful assistant with the ability to call functions to get the result you want. When the task is done respond with just TERMINATE""",
        model_client=model_client,
        functions=[{"func": get_weather, "description": "Get the weather in a city."}],
    )
    function_executor = FunctionCallingAgent(name="caller", functions=[get_weather])
    chat = TwoAgentChat(assistant, function_executor, initial_message="What is the weather in Seattle?")
    await run_in_terminal(chat)
    print(chat.termination_result)


if __name__ == "__main__":
    asyncio.run(main())
