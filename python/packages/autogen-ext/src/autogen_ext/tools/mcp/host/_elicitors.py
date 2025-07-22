from abc import ABC, abstractmethod
from typing import Any, Dict

from autogen_agentchat.base import Response
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import BaseGroupChat
from autogen_agentchat.teams._group_chat._events import GroupChatMessage
from autogen_core import (
    AgentId,
    Component,
    ComponentBase,
    ComponentModel,
)
from autogen_core._default_topic import DefaultTopicId
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from autogen_core.models._types import LLMMessage
from pydantic import BaseModel

from mcp import types as mcp_types


class Elicitor(ABC, ComponentBase[BaseModel]):
    """Abstract base class for handling MCP elicitation requests.

    Elicitors are responsible for processing elicitation requests from MCP servers,
    which typically involve prompting for user input or structured responses.
    """

    @staticmethod
    def elicit_result_json_schema(params: mcp_types.ElicitRequestParams) -> Dict[str, Any]:
        json_schema = mcp_types.ElicitResult.model_json_schema()
        json_schema["properties"]["content"] = params.requestedSchema
        return json_schema

    @abstractmethod
    async def elicit(self, params: mcp_types.ElicitRequestParams) -> mcp_types.ElicitResult: ...


class GroupChatAgentElicitorConfig(BaseModel):
    """Configuration for group chat agent elicitors.

    Args:
        recipient: The recipient agent name for elicitation requests
        model_client: Chat completion client component or configuration dictionary
    """

    recipient: str
    model_client: ComponentModel | Dict[str, Any]


class GroupChatAgentElicitor(Elicitor, Component[GroupChatAgentElicitorConfig]):
    """Elicitor that forwards elicitation requests to an AutoGen group chat agent.

    This elicitor sends elicitation requests as messages to a specified agent
    within a group chat, allowing agents to handle complex prompting scenarios
    from MCP servers. The response is then converted to the required JSON format
    using a model client.

    Args:
        recipient: The agent name to send elicitation requests to
        model_client: Chat completion client for converting responses to JSON format
    """

    component_type = "elicitor"
    component_config_schema = GroupChatAgentElicitorConfig
    component_provider_override = "autogen_ext.tools.mcp.AgentElicitor"

    def __init__(self, recipient: str, model_client: ChatCompletionClient) -> None:
        self._recipient = recipient
        self._model_client = model_client
        self._group_chat: BaseGroupChat | None = None

    def set_group_chat(self, group_chat: BaseGroupChat) -> None:
        """Set the group chat instance for the elicitor.

        This method allows setting the group chat after initialization,
        which is useful when the group chat is not known at init time.

        Args:
            group_chat: The BaseGroupChat instance to use for elicitation
        """
        self._group_chat = group_chat

    async def elicit(self, params: mcp_types.ElicitRequestParams) -> mcp_types.ElicitResult:
        if self._group_chat is None:
            raise RuntimeError("Group chat must be set before calling elicit. Use set_group_chat() method.")

        runtime = self._group_chat._runtime  # type: ignore[reportPrivateUsage]

        recipient_agent_id = AgentId(
            type=f"{self._recipient}_{self._group_chat._team_id}",  # type: ignore[reportPrivateUsage]
            key=self._group_chat._team_id,  # type: ignore[reportPrivateUsage]
        )

        # Create TextMessage from the elicitation request
        elicit_message = TextMessage(content=params.message, source="user")

        # Publish elicit message to conversation history
        await runtime.publish_message(
            GroupChatMessage(message=elicit_message),
            topic_id=DefaultTopicId(type=self._group_chat._group_chat_manager_topic_type),  # type: ignore[reportPrivateUsage]
        )

        # Send RPC message to recipient agent and get response
        recipient_response = await runtime.send_message(
            elicit_message,
            recipient=recipient_agent_id,
        )

        assert isinstance(recipient_response, Response), "Expected Response"

        # Publish response message to conversation history
        await runtime.publish_message(
            GroupChatMessage(message=recipient_response.chat_message),
            topic_id=DefaultTopicId(type=self._group_chat._group_chat_manager_topic_type),  # type: ignore[reportPrivateUsage]
        )

        messages: list[LLMMessage] = [
            SystemMessage(
                content=f"Convert all user messages to the following json format: \n{self.elicit_result_json_schema(params)}"
            ),
            AssistantMessage(
                content=params.message,
                source=self._recipient,
            ),
            UserMessage(content=recipient_response.chat_message.to_text(), source="user"),
        ]
        result = await self._model_client.create(messages=messages)
        assert isinstance(result.content, str), "Expected text output"
        result_text = result.content.strip().removeprefix("```json").strip("`")
        return mcp_types.ElicitResult.model_validate_json(result_text)

    def _to_config(self) -> BaseModel:
        return GroupChatAgentElicitorConfig(
            recipient=self._recipient,
            model_client=self._model_client.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: GroupChatAgentElicitorConfig) -> "GroupChatAgentElicitor":
        return cls(recipient=config.recipient, model_client=ChatCompletionClient.load_component(config.model_client))


class ChatCompletionClientElicitorConfig(BaseModel):
    """Configuration for chat completion client elicitors.

    Args:
        model_client: Chat completion client component or configuration dictionary
        system_prompt: Optional system prompt for providing context to the model
    """

    model_client: ComponentModel | Dict[str, Any]
    system_prompt: str | None


class ChatCompletionClientElicitor(Elicitor, Component[ChatCompletionClientElicitorConfig]):
    """Elicitor that uses a chat completion client to handle elicitation requests directly.

    This elicitor processes elicitation requests by prompting a language model
    directly, optionally with a system prompt for context. It expects structured
    JSON output conforming to the ElicitResult schema.

    Args:
        model_client: Chat completion client for generating responses
        system_prompt: Optional system prompt to provide context for elicitation
    """

    component_type = "elicitor"
    component_config_schema = ChatCompletionClientElicitorConfig

    def __init__(self, model_client: ChatCompletionClient, system_prompt: str | None = None):
        self.model_client = model_client
        self.system_prompt = system_prompt

    async def elicit(self, params: mcp_types.ElicitRequestParams) -> mcp_types.ElicitResult:
        messages: list[LLMMessage] = []
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        user_message_content = params.message
        user_message_content += f"\n\nRespond in this json format:\n{self.elicit_result_json_schema(params)}"
        messages.append(UserMessage(source="user", content=user_message_content))

        result = await self.model_client.create(messages=messages)
        assert isinstance(result.content, str), "Expected text output"
        result_text = result.content.strip().removeprefix("```json").strip("`")
        return mcp_types.ElicitResult.model_validate_json(result_text)

    def _to_config(self) -> BaseModel:
        return ChatCompletionClientElicitorConfig(
            model_client=self.model_client.dump_component(), system_prompt=self.system_prompt
        )

    @classmethod
    def _from_config(cls, config: ChatCompletionClientElicitorConfig) -> "ChatCompletionClientElicitor":
        return cls(
            model_client=ChatCompletionClient.load_component(config.model_client), system_prompt=config.system_prompt
        )
