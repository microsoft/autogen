import asyncio
from dataclasses import asdict
import os

from autogen.experimental import AssistantAgent, OpenAI, TwoAgentChat
from autogen.experimental.agents.chat_agent import ChatAgent
from autogen.experimental.agents.execution_agent import ExecutionAgent
from autogen.experimental.agents.user_input_agent import UserInputAgent
from autogen.experimental.types import Message, UserMessage, AssistantMessage, SystemMessage, FunctionCallMessage

from autogen.experimental.chat_result import ChatResult
from autogen.experimental.terminations import DefaultTermination
from autogen.experimental.drivers import run_in_terminal
from autogen.experimental.function_executors.in_process_function_executor import InProcessFunctionExecutor

import aioconsole
from termcolor import cprint


def get_weather(city: str) -> str:
    return f"The weather in {city} is 75 degrees Fahrenheit."


def message_type(message: Message) -> str:
    if isinstance(message, SystemMessage):
        return "System"
    elif isinstance(message, UserMessage):
        return "User"
    elif isinstance(message, AssistantMessage):
        return "Assistant"
    elif isinstance(message, FunctionCallMessage):
        return "FunctionCall"
    else:
        return "Unknown"


def message_content(message: Message) -> str:
    if isinstance(message, SystemMessage):
        return message.content
    elif isinstance(message, UserMessage):
        assert isinstance(message.content, str)
        return message.content
    elif isinstance(message, AssistantMessage):
        if message.content is not None:
            return message.content
        elif message.function_calls is not None:
            return "\n".join([str(asdict(x)) for x in message.function_calls])
        else:
            return "Unknown"
    elif isinstance(message, FunctionCallMessage):
        return "\n".join([call.content for call in message.call_results])
    else:
        return "Unknown"


def print_chat_tree_simple(chat: ChatResult, depth: int = 0) -> None:
    for message, context in zip(chat.conversation.messages, chat.conversation.contexts):
        # Just print the message
        agent_name = context.sender.name if context.sender is not None else "Unknown"
        message_type_str = message_type(message)
        cprint(f"{'  ' * depth}({agent_name}): ", "green", end="")
        cprint(f"{message_type_str} = ", "blue", end="")
        cprint(f"{message_content(message)}", "yellow")
        if context.nested_chat_result is not None:
            print_chat_tree_simple(context.nested_chat_result, depth + 1)


async def main() -> None:
    model_client = OpenAI(model="gpt-4-turbo", api_key=os.environ["OPENAI_API_KEY"])

    assistant = AssistantAgent(
        name="agent",
        system_message="""You are a helpful assistant with the ability to call functions to get the result you want.""",
        model_client=model_client,
        functions=[{"func": get_weather, "description": "Get the weather in a city."}],
    )
    executor = ExecutionAgent(
        name="function_executor", code_executor=None, function_executor=InProcessFunctionExecutor([get_weather])
    )

    # We use two turns because we just want 1 round of call+executor
    chat = TwoAgentChat(assistant, executor, termination_manager=DefaultTermination(max_turns=2))
    function_caller_and_executor = ChatAgent(name="function_caller_and_executor", chat=chat)

    async def user_input(prompt: str) -> str:
        res = await aioconsole.ainput(prompt)  # type: ignore
        if not isinstance(res, str):
            raise ValueError("Expected a string")
        return res

    user = UserInputAgent(name="user", human_input_callback=user_input)
    chat = TwoAgentChat(user, function_caller_and_executor)

    await run_in_terminal(chat)
    print_chat_tree_simple(chat.result)


if __name__ == "__main__":
    asyncio.run(main())
