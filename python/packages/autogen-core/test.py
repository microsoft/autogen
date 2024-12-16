from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.models.openai._azure_token_provider import AzureTokenProvider
from azure.identity import DefaultAzureCredential

from autogen_core.models import ChatCompletionClient


az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="{your-azure-deployment}",
    model="gpt-4o",
    api_version="2024-06-01",
    azure_endpoint="https://{your-custom-endpoint}.openai.azure.com/",
    azure_ad_token_provider=AzureTokenProvider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"),
)

comp = az_model_client.dump_component()
loaded = ChatCompletionClient.load_component(comp)

print(loaded.__class__.__name__)