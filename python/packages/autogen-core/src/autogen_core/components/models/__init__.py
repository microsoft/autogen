from typing_extensions import deprecated

from ...models import (
    AssistantMessage as AssistantMessageAlias,
)
from ...models import ChatCompletionClient as ChatCompletionClientAlias
from ...models import (
    ChatCompletionTokenLogprob as ChatCompletionTokenLogprobAlias,
)
from ...models import (
    CreateResult as CreateResultAlias,
)
from ...models import (
    FinishReasons as FinishReasonsAlias,
)
from ...models import (
    FunctionExecutionResult as FunctionExecutionResultAlias,
)
from ...models import (
    FunctionExecutionResultMessage as FunctionExecutionResultMessageAlias,
)
from ...models import (
    LLMMessage as LLMMessageAlias,
)
from ...models import ModelCapabilities as ModelCapabilitiesAlias
from ...models import (
    RequestUsage as RequestUsageAlias,
)
from ...models import (
    SystemMessage as SystemMessageAlias,
)
from ...models import (
    TopLogprob as TopLogprobAlias,
)
from ...models import (
    UserMessage as UserMessageAlias,
)


@deprecated(
    "autogen_core.components.models.ChatCompletionClient moved to autogen_core.models.ChatCompletionClient. This alias will be removed in 0.4.0."
)
class ChatCompletionClient(ChatCompletionClientAlias):
    pass


@deprecated(
    "autogen_core.components.models.ModelCapabilities moved to autogen_core.models.ModelCapabilities. This alias will be removed in 0.4.0."
)
class ModelCapabilities(ModelCapabilitiesAlias):
    pass


@deprecated(
    "autogen_core.components.models.SystemMessage moved to autogen_core.models.SystemMessage. This alias will be removed in 0.4.0."
)
class SystemMessage(SystemMessageAlias):
    pass


@deprecated(
    "autogen_core.components.models.UserMessage moved to autogen_core.models.UserMessage. This alias will be removed in 0.4.0."
)
class UserMessage(UserMessageAlias):
    pass


@deprecated(
    "autogen_core.components.models.AssistantMessage moved to autogen_core.models.AssistantMessage. This alias will be removed in 0.4.0."
)
class AssistantMessage(AssistantMessageAlias):
    pass


@deprecated(
    "autogen_core.components.models.FunctionExecutionResult moved to autogen_core.models.FunctionExecutionResult. This alias will be removed in 0.4.0."
)
class FunctionExecutionResult(FunctionExecutionResultAlias):
    pass


@deprecated(
    "autogen_core.components.models.FunctionExecutionResultMessage moved to autogen_core.models.FunctionExecutionResultMessage. This alias will be removed in 0.4.0."
)
class FunctionExecutionResultMessage(FunctionExecutionResultMessageAlias):
    pass


LLMMessage = LLMMessageAlias


@deprecated(
    "autogen_core.components.models.RequestUsage moved to autogen_core.models.RequestUsage. This alias will be removed in 0.4.0."
)
class RequestUsage(RequestUsageAlias):
    pass


FinishReasons = FinishReasonsAlias


@deprecated(
    "autogen_core.components.models.CreateResult moved to autogen_core.models.CreateResult. This alias will be removed in 0.4.0."
)
class CreateResult(CreateResultAlias):
    pass


@deprecated(
    "autogen_core.components.models.TopLogprob moved to autogen_core.models.TopLogprob. This alias will be removed in 0.4.0."
)
class TopLogprob(TopLogprobAlias):
    pass


@deprecated(
    "autogen_core.components.models.ChatCompletionTokenLogprob moved to autogen_core.models.ChatCompletionTokenLogprob. This alias will be removed in 0.4.0."
)
class ChatCompletionTokenLogprob(ChatCompletionTokenLogprobAlias):
    pass


__all__ = [
    "ModelCapabilities",
    "ChatCompletionClient",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "FunctionExecutionResult",
    "FunctionExecutionResultMessage",
    "LLMMessage",
    "RequestUsage",
    "FinishReasons",
    "CreateResult",
    "TopLogprob",
    "ChatCompletionTokenLogprob",
]
