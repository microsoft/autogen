from typing_extensions import deprecated

from .openai import AzureOpenAIChatCompletionClient as AzureOpenAIChatCompletionClientAlias
from .openai import OpenAIChatCompletionClient as OpenAIChatCompletionClientAlias


@deprecated(
    "autogen_ext.models.OpenAIChatCompletionClient moved to autogen_ext.models.openai.OpenAIChatCompletionClient. This alias will be removed in 0.4.0."
)
class OpenAIChatCompletionClient(OpenAIChatCompletionClientAlias):
    pass


@deprecated(
    "autogen_ext.models.AzureOpenAIChatCompletionClient moved to autogen_ext.models.openai.AzureOpenAIChatCompletionClient. This alias will be removed in 0.4.0."
)
class AzureOpenAIChatCompletionClient(AzureOpenAIChatCompletionClientAlias):
    pass
