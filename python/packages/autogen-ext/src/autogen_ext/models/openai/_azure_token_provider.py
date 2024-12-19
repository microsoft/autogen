from typing import List

from autogen_core import Component
from azure.core.credentials import TokenProvider
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from pydantic import BaseModel
from typing_extensions import Self


class TokenProviderConfig(BaseModel):
    provider_kind: str
    scopes: List[str]


class AzureTokenProvider(Component[TokenProviderConfig]):
    component_type = "token_provider"
    config_schema = TokenProviderConfig

    def __init__(self, credential: TokenProvider, *scopes: str):
        self.credential = credential
        self.scopes = list(scopes)
        self.provider = get_bearer_token_provider(self.credential, *self.scopes)

    def __call__(self) -> str:
        return self.provider()

    def _to_config(self) -> TokenProviderConfig:
        """Dump the configuration that would be requite to create a new instance of a component matching the configuration of this instance.

        Returns:
            T: The configuration of the component.
        """

        if isinstance(self.credential, DefaultAzureCredential):
            # NOTE: we are not currently inspecting the chained credentials, so this could result in a loss of information
            return TokenProviderConfig(provider_kind="DefaultAzureCredential", scopes=self.scopes)
        else:
            raise ValueError("Only DefaultAzureCredential is supported")

    @classmethod
    def _from_config(cls, config: TokenProviderConfig) -> Self:
        """Create a new instance of the component from a configuration object.

        Args:
            config (T): The configuration object.

        Returns:
            Self: The new instance of the component.
        """

        if config.provider_kind == "DefaultAzureCredential":
            return cls(DefaultAzureCredential(), *config.scopes)
        else:
            raise ValueError("Only DefaultAzureCredential is supported")
