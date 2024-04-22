from autogen.experimental.chat import ChatOrchestratorStream
from autogen.experimental.types import AssistantMessage, FunctionCallMessage, UserMessage


async def legacy_run_in_terminal(chat: ChatOrchestratorStream) -> str:
    print("\n")
    while not chat.done:
        message = await chat.step()

        # BUG: sender name should come from the step result
        sender_name = message.__class__.__name__
        print(f"{sender_name}:\n")

        content = None

        if isinstance(message, UserMessage) or isinstance(message, AssistantMessage):
            if isinstance(message.content, str):
                content = message.content

        elif isinstance(message, FunctionCallMessage):
            content = ""
            call_results = message.call_results
            for call_result in call_results:
                content += call_result.content + "\n"

        if isinstance(content, str):
            print(content)
            print("-" * 80)

    return chat.result.summary
