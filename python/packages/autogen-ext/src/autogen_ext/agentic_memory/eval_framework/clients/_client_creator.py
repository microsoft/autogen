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

    def add_shared_args(self, args):
        args["model"] = self.settings["model"]
        args["max_completion_tokens"] = self.settings["max_completion_tokens"]
        args["max_retries"] = self.settings["max_retries"]

    def add_family_args(self, args):
        # Does the model name start with 'o1'?
        if not args["model"].startswith("o1"):
            # No. A few more things can be specified.
            args["temperature"] = self.settings["temperature"]
            args["presence_penalty"] = self.settings["presence_penalty"]
            args["frequency_penalty"] = self.settings["frequency_penalty"]
            args["top_p"] = self.settings["top_p"]

    def create_oai_client(self):
        # Create an OpenAI client
        args = {"api_key": self.settings["api_key"]}
        self.add_shared_args(args)
        self.add_family_args(args)

        client = OpenAIChatCompletionClient(**args)

        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through OpenAI")
        return client


    def create_aoai_client(self):
        # Create an Azure OpenAI client
        model = self.settings["model"]
        if model == "gpt-4o-2024-08-06":
            azure_deployment = 'gpt-4o-2024-08-06-eval'  # This is DeploymentName in the table at https://aka.ms/trapi/models
            azure_endpoint = "https://agentic2.openai.azure.com/"
        elif model == "gpt-4o-2024-05-13":
            azure_deployment = 'gpt-4o-2024-05-13-eval'
            azure_endpoint = "https://agentic1.openai.azure.com/"
        elif model == "o1-preview":
            azure_deployment = 'o1-preview-2024-09-12-eval'
            azure_endpoint = "https://agentic1.openai.azure.com/"
        else:
            assert False, "Unsupported model"

        token_provider = get_bearer_token_provider(DefaultAzureCredential(),
                                                   "https://cognitiveservices.azure.com/.default")
        api_version = '2024-12-01-preview'  # From https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release

        args = {
            "azure_ad_token_provider": token_provider,
            "azure_deployment": azure_deployment,
            "azure_endpoint": azure_endpoint,
            "api_version": api_version,
        }
        self.add_shared_args(args)
        self.add_family_args(args)

        client = AzureOpenAIChatCompletionClient(**args)

        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through Azure OpenAI")
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
        api_version = '2024-12-01-preview'  # From https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
        model = self.settings["model"]
        if model == "gpt-4o-2024-08-06":
            azure_deployment = 'gpt-4o_2024-08-06'  # This is DeploymentName in the table at https://aka.ms/trapi/models
        elif model == "gpt-4o-2024-05-13":
            azure_deployment = 'gpt-4o_2024-05-13'
        elif model == "o1-preview":
            azure_deployment = 'o1-preview_2024-09-12'
        elif model == "o1":
            azure_deployment = 'o1_2024-12-17'
        else:
            assert False, "Unsupported model"
        trapi_suffix = 'msraif/shared'  # This is TRAPISuffix (without /openai) in the table at https://aka.ms/trapi/models
        endpoint = f'https://trapi.research.microsoft.com/{trapi_suffix}'

        args = {
            "azure_ad_token_provider": token_provider,
            "azure_deployment": azure_deployment,
            "azure_endpoint": endpoint,
            "api_version": api_version,
        }
        self.add_shared_args(args)
        self.add_family_args(args)

        client = AzureOpenAIChatCompletionClient(**args)

        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through TRAPI")
        return client

