from autogen_core.components.models import UserMessage

from exts.models.mistralai.mistral_ai import MistralAIChatCompletionClient
from mistralai import Mistral





def get_model_client() -> MistralAIChatCompletionClient:
    return MistralAIChatCompletionClient(
        client=Mistral(api_key="mqsnQ0WeuaGCbUmrvN3bcBHgkfKCClx7"),
        model="mistral-large-latest",
        create_args={"temperature":0.3,"max_tokens":200}
    )


model = get_model_client()
messages = [
    UserMessage(content="What is the capital of France?",source=None),
]

import asyncio
response =  asyncio.run(model.create(messages=messages))
print(response)
