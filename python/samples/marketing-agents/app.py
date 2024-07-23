import os

from agnext.components.models import AzureOpenAIChatCompletionClient
from agnext.core import AgentRuntime
from auditor import AuditAgent
from graphic_designer import GraphicDesignerAgent
from openai import AsyncAzureOpenAI


async def build_app(runtime: AgentRuntime) -> None:
    chat_client = AzureOpenAIChatCompletionClient(
        model="gpt-4-32",
        azure_endpoint=os.environ["CHAT_ENDPOINT"],
        api_version="2024-02-01",
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        },
        api_key=os.environ["CHAT_ENDPOINT_KEY"],
    )

    image_client = AsyncAzureOpenAI(
        azure_endpoint=os.environ["IMAGE_ENDPOINT"],
        azure_deployment="dall-e-3",
        api_key=os.environ["IMAGE_ENDPOINT_KEY"],
        api_version="2024-02-01",
    )

    await runtime.register("GraphicDesigner", lambda: GraphicDesignerAgent(client=image_client))
    await runtime.register("Auditor", lambda: AuditAgent(model_client=chat_client))

    await runtime.get("GraphicDesigner")
    await runtime.get("Auditor")
