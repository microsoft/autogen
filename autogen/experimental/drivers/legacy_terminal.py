from autogen.experimental.chat import ChatOrchestratorStream
from autogen.experimental.types import AssistantMessage, FunctionCallMessage, UserMessage


async def legacy_run_in_terminal(chat: ChatOrchestratorStream) -> str:
    print("\n")
    while not chat.done:
        step = await chat.step()
        print(f"{step.__class__.__name__}:\n")

        content = None

        if isinstance(step, UserMessage) or isinstance(step, AssistantMessage):
            if isinstance(step.content, str):
                content = step.content

        elif isinstance(step, FunctionCallMessage):
            content = ""
            call_results = step.call_results
            for call_result in call_results:
                content += call_result.content + "\n"

        if isinstance(content, str):
            print(content)
            print("-" * 80)

    return chat.result.summary
