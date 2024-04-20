from autogen.experimental.chat import ChatOrchestratorStream


async def legacy_run_in_terminal(chat: ChatOrchestratorStream) -> str:
    print("\n")
    while not chat.done:
        step = await chat.step()
        print(f"{step.__class__.__name__}:\n")
        print(step.content)
        print("-" * 80)

    return chat.result.summary
