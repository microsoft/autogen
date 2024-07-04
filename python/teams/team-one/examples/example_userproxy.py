import asyncio
import logging

# from typing import Any, Dict, List, Tuple, Union
from agnext.application import SingleThreadedAgentRuntime
from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components.models import (
    AzureOpenAIChatCompletionClient,
    ModelCapabilities,
)
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from team_one.agents.coder import Coder
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.agents.user_proxy import UserProxy
from team_one.messages import OrchestrationEvent, RequestReplyMessage


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create the AzureOpenAI client, with AAD auth
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAIChatCompletionClient(
        api_version="2024-02-15-preview",
        azure_endpoint="https://aif-complex-tasks-west-us-3.openai.azure.com/",
        model="gpt-4o-2024-05-13",
        model_capabilities=ModelCapabilities(function_calling=True, json_output=True, vision=True),
        azure_ad_token_provider=token_provider,
    )

    # Register agents.
    coder = runtime.register_and_get_proxy(
        "Coder",
        lambda: Coder(model_client=client),
    )
    user_proxy = runtime.register_and_get_proxy(
        "UserProxy",
        lambda: UserProxy(),
    )

    runtime.register("orchestrator", lambda: RoundRobinOrchestrator([coder, user_proxy]))

    run_context = runtime.start()
    await runtime.send_message(RequestReplyMessage(), user_proxy.id)
    await run_context.stop_when_idle()


class MyHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if isinstance(record.msg, OrchestrationEvent):
                print(
                    f"""---------------------------------------------------------------------------
\033[91m{record.msg.source}:\033[0m

{record.msg.message}""",
                    flush=True,
                )
        except Exception:
            self.handleError(record)


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    my_handler = MyHandler()
    logger.handlers = [my_handler]
    asyncio.run(main())
