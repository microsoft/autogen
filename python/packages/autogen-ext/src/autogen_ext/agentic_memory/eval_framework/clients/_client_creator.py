from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, get_bearer_token_provider
from ._client_wrapper import ClientWrapper


class ClientCreator:
    def __init__(self, settings, page_log):
        self.settings = settings
        self.page_log = page_log

    def create_client(self):
        client = None
        provider = self.settings["provider"]
        if provider == "openai":
            client = self.create_oai_client()
        elif provider == "azure_openai":
            client = self.create_aoai_client()
        elif provider == "trapi":
            client = self.create_trapi_client()
        else:
            assert False, "Invalid client provider"

        # Check if the client should be wrapped.
        if "ClientWrapper" in self.settings:
            wrapper_settings = self.settings["ClientWrapper"]
            if wrapper_settings["enabled"]:
                # Wrap the client.
                client = ClientWrapper(
                    client, wrapper_settings["mode"], wrapper_settings["session_name"], self.page_log)

        return client


    def create_oai_client(self):
        # Create an OpenAI client
        client = OpenAIChatCompletionClient(
            model=self.settings["model"],
            api_key=self.settings["api_key"],
            temperature=self.settings["temperature"],
            max_tokens=self.settings["max_tokens"],
            presence_penalty=self.settings["presence_penalty"],
            frequency_penalty=self.settings["frequency_penalty"],
            top_p=self.settings["top_p"],
            max_retries=self.settings["max_retries"],
        )
        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through OpenAI")
        self.page_log.append_entry_line("  temperature:  {}".format(self.settings["temperature"]))
        return client


    def create_aoai_client(self):
        # Create an Azure OpenAI client
        model = self.settings["model"]
        azure_deployment = model + "-eval"
        if model == "gpt-4o-2024-08-06":
            azure_endpoint = "https://agentic2.openai.azure.com/"
        else:
            azure_endpoint = "https://agentic1.openai.azure.com/"
        token_provider = get_bearer_token_provider(DefaultAzureCredential(),
                                                   "https://cognitiveservices.azure.com/.default")
        client = AzureOpenAIChatCompletionClient(
            azure_endpoint=azure_endpoint,
            azure_ad_token_provider=token_provider,
            azure_deployment=azure_deployment,
            api_version="2024-06-01",
            model=model,
            temperature=self.settings["temperature"],
            max_tokens=self.settings["max_tokens"],
            presence_penalty=self.settings["presence_penalty"],
            frequency_penalty=self.settings["frequency_penalty"],
            top_p=self.settings["top_p"],
            max_retries=self.settings["max_retries"],
        )
        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through Azure OpenAI")
        self.page_log.append_entry_line("  temperature:  {}".format(self.settings["temperature"]))
        return client


    def create_trapi_client(self):
        # Create an Azure OpenAI client through TRAPI
        token_provider = get_bearer_token_provider(ChainedTokenCredential(
            AzureCliCredential(),
            DefaultAzureCredential(
                exclude_cli_credential=True,
                # Exclude other credentials we are not interested in.
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_developer_cli_credential=True,
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_visual_studio_code_credentials=True,
                # managed_identity_client_id=os.environ.get("DEFAULT_IDENTITY_CLIENT_ID"),  # See the TRAPI docs
            )
        ), "api://trapi/.default")
        model = self.settings["model"]
        if model == "gpt-4o-2024-08-06":
            azure_deployment = 'gpt-4o_2024-08-06'  # This is DeploymentName in the table at https://aka.ms/trapi/models
        elif model == "gpt-4o-2024-05-13":
            azure_deployment = 'gpt-4o_2024-05-13'
        elif model == "o1-preview":
            azure_deployment = 'o1-preview_2024-09-12'
        trapi_suffix = 'msraif/shared'  # This is TRAPISuffix (without /openai) in the table at https://aka.ms/trapi/models
        endpoint = f'https://trapi.research.microsoft.com/{trapi_suffix}'
        api_version = '2024-10-21'  # From https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
        client = AzureOpenAIChatCompletionClient(
            azure_ad_token_provider=token_provider,
            model=model,
            azure_deployment=azure_deployment,
            azure_endpoint=endpoint,
            api_version=api_version,
            temperature=self.settings["temperature"],
            max_tokens=self.settings["max_tokens"],
            presence_penalty=self.settings["presence_penalty"],
            frequency_penalty=self.settings["frequency_penalty"],
            top_p=self.settings["top_p"],
            max_retries=self.settings["max_retries"],
        )
        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through TRAPI")
        self.page_log.append_entry_line("  temperature:  {}".format(self.settings["temperature"]))
        return client

