from langchain_openai import AzureChatOpenAI
import os
from llm.models.settings import open_ai_ep
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)



os.environ["AZURE_OPENAI_ENDPOINT"] = open_ai_ep



class OpenAIClientBuilder:
    def __init__(self, deployment_name=None):
        if deployment_name is None:
            self.deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]
        else:
            self.deployment_name = deployment_name

        aoi_llm = AzureChatOpenAI(openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"], azure_deployment=self.deployment_name, temperature=0.1, azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], azure_ad_token_provider=token_provider
)
        self.llm = aoi_llm


    def get_client(self):
        return self.llm
