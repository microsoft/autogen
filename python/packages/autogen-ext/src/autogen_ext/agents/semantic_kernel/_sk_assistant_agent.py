import base64
from collections.abc import AsyncGenerator
from dataclasses import asdict
from typing import Any, Optional, Sequence

from autogen_agentchat.agents._base_chat_agent import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage, HandoffMessage, StopMessage, TextMessage, ToolCallSummaryMessage
from autogen_core import CancellationToken

from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents import ImageContent, TextContent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.exceptions import KernelServiceNotFoundError
from semantic_kernel.kernel import Kernel


class SKAssistantAgent(BaseChatAgent):
    """
    SKAssistantAgent is a specialized agent that leverages Semantic Kernel for
    conversation handling and response generation. It extends the autogen
    ``BaseChatAgent`` class and uses a single Semantic Kernel ``ChatHistory``
    to store and manage dialogue context.

    Installation:

    .. code-block:: bash

        pip install "autogen-ext[semantic-kernel-core]"

    For other model providers and semantic kernel features install the appropriate extra or install all providers with: semantic-kernel-all

    This agent supports streaming responses (token by token) and final message
    generation by calling the configured Semantic Kernel chat completion service.

    Args:
        name (str): The name of the agent.
        description (str): A description of the agent's capabilities or purpose.
        kernel (Kernel): The Semantic Kernel instance to use for chat completions.
        service_id (str, optional): The ID of the chat completion service. Defaults to "default".
        instructions (str, optional): Optional system-level instructions for the assistant.
        execution_settings (PromptExecutionSettings, optional):
            Optional prompt execution settings to override defaults.

    Example usage:

    The following example demonstrates how to create and use an ``SKAssistantAgent``
    in conjunction with a Semantic Kernel. It sets up an Azure-based chat model,
    adds a Bing search plugin, and then streams the agent's response to the console:

    .. code-block:: python

        import asyncio
        import os

        from autogen_agentchat.ui._console import Console
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
        from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, AzureChatPromptExecutionSettings
        from semantic_kernel.connectors.search.bing import BingSearch
        from semantic_kernel.functions import KernelParameterMetadata, KernelPlugin
        from autogen_ext.agents.semantic_kernel import SKAssistantAgent


        async def main():
            # Initialize the kernel
            kernel = Kernel()

            # Configure OpenAI chat completion
            ai_service = AzureChatCompletion(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                deployment_name="gpt-4o-mini",
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_VERSION"),
            )
            kernel.add_service(ai_service)

            # Configure Bing search
            bing_api_key = os.getenv("BING_API_KEY")
            # Add the WebSearchEnginePlugin to the kernel
            kernel.add_plugin(
                KernelPlugin.from_text_search_with_search(
                    BingSearch(bing_api_key),
                    plugin_name="bing",
                    description="Get details about Semantic Kernel concepts.",
                    parameters=[
                        KernelParameterMetadata(
                            name="query",
                            description="The search query.",
                            type="str",
                            is_required=True,
                            type_object=str,
                        ),
                        KernelParameterMetadata(
                            name="top",
                            description="Number of results to return.",
                            type="int",
                            is_required=False,
                            default_value=2,
                            type_object=int,
                        ),
                        KernelParameterMetadata(
                            name="skip",
                            description="Number of results to skip.",
                            type="int",
                            is_required=False,
                            default_value=0,
                            type_object=int,
                        ),
                    ],
                )
            )

            # Create the SKAssistantAgent
            agent = SKAssistantAgent(
                name="MyAssistant",
                description="An AI assistant that can search the web and answer questions",
                kernel=kernel,
                execution_settings=AzureChatPromptExecutionSettings(
                    function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=True)  # type: ignore
                ),
            )

            query = "What are the latest news on autogen?"
            await Console(agent.run_stream(task=query))


        if __name__ == "__main__":
            asyncio.run(main())

    """

    def __init__(
        self,
        name: str,
        description: str,
        kernel: Kernel,
        service_id: str = "default",
        instructions: Optional[str] = None,
        execution_settings: Optional[PromptExecutionSettings] = None,
    ) -> None:
        super().__init__(name, description)
        self._kernel = kernel
        self._service_id = service_id
        self._instructions = instructions
        self._execution_settings = execution_settings

        # Maintain the entire conversation as a ChatHistory (SK concept).
        self._chat_history: ChatHistory = ChatHistory()

        # If instructions are provided, set them as the first system message
        if instructions:
            self._chat_history.add_system_message(instructions)

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return [TextMessage]

    async def on_messages(
        self,
        messages: Sequence[ChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        """
        Handle incoming messages, add them to our ChatHistory, call SK for a response,
        and return a final single text response.
        """
        # 1) Convert & store new agent messages in ChatHistory
        for msg in messages:
            sk_msg = self._convert_chat_message_to_sk_chat_message_content(AuthorRole.USER, msg)
            self._chat_history.add_message(sk_msg)

        # 2) Retrieve the SK chat completion service
        chat_completion_service = self._kernel.get_service(
            service_id=self._service_id,
            type=ChatCompletionClientBase,
        )
        if not chat_completion_service:
            raise KernelServiceNotFoundError(f"Chat completion service not found with service_id: {self._service_id}")

        assert isinstance(chat_completion_service, ChatCompletionClientBase)

        # 3) Get or create the PromptExecutionSettings
        settings = (
            self._execution_settings
            or self._kernel.get_prompt_execution_settings_from_service_id(self._service_id)
            or chat_completion_service.instantiate_prompt_execution_settings(  # type: ignore
                service_id=self._service_id,
                extension_data={"ai_model_id": chat_completion_service.ai_model_id},
            )
        )

        # 4) Invoke SK to get an assistant response
        sk_responses = await chat_completion_service.get_chat_message_contents(
            chat_history=self._chat_history,
            settings=settings,
            kernel=self._kernel,
        )
        # Convert SK's list of responses into a single final text
        assistant_reply = "\n".join(r.content for r in sk_responses if r.content)
        reply_message = TextMessage(content=assistant_reply, source=self.name)

        # 5) Add the new assistant message into our chat history
        if assistant_reply.strip():
            self._chat_history.add_message(
                self._convert_chat_message_to_sk_chat_message_content(AuthorRole.ASSISTANT, reply_message)
            )

        # 6) Return an autogen Response containing the text
        return Response(chat_message=reply_message)

    async def on_messages_stream(
        self,
        messages: Sequence[ChatMessage],
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[ChatMessage | Response, None]:
        """
        Handle new messages in streaming mode, yielding a final Response.
        """
        # 1) Convert & store new agent messages
        for msg in messages:
            sk_msg = self._convert_chat_message_to_sk_chat_message_content(AuthorRole.USER, msg)
            self._chat_history.add_message(sk_msg)

        # 2) Retrieve chat completion service
        chat_completion_service = self._kernel.get_service(
            service_id=self._service_id,
            type=ChatCompletionClientBase,
        )
        if not chat_completion_service:
            raise KernelServiceNotFoundError(f"Chat completion service not found with service_id: {self._service_id}")

        assert isinstance(chat_completion_service, ChatCompletionClientBase)

        settings = (
            self._execution_settings
            or self._kernel.get_prompt_execution_settings_from_service_id(self._service_id)
            or chat_completion_service.instantiate_prompt_execution_settings(  # type: ignore
                service_id=self._service_id,
                extension_data={"ai_model_id": chat_completion_service.ai_model_id},
            )
        )

        # 3) Stream the SK response
        accumulated_reply: list[str] = []
        async for sk_message_list in chat_completion_service.get_streaming_chat_message_contents(
            chat_history=self._chat_history,
            settings=settings,
            kernel=self._kernel,
        ):
            for sk_message in sk_message_list:
                if sk_message.content:
                    accumulated_reply.append(sk_message.content)

        # 4) After streaming ends, save the entire assistant message
        final_text = "".join(accumulated_reply).strip()
        if final_text:
            self._chat_history.add_assistant_message(final_text, name=self.name)

        # 5) Finally, yield the single autogen Response
        yield Response(chat_message=TextMessage(content=final_text, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Clear the entire conversation history."""
        self._chat_history.messages.clear()

    @staticmethod
    def _convert_chat_message_to_sk_chat_message_content(
        role: AuthorRole, chat_message: ChatMessage
    ) -> ChatMessageContent:
        # Prepare a place to store metadata (e.g., usage)
        metadata: dict[str, Any] = {}
        if chat_message.models_usage is not None:
            metadata["models_usage"] = asdict(chat_message.models_usage)

        items: list[TextContent | ImageContent] = []
        msg_type = chat_message.type

        match msg_type:
            case "TextMessage":
                assert isinstance(chat_message, TextMessage)
                items.append(TextContent(text=chat_message.content))

            case "MultiModalMessage":
                for entry in chat_message.content:
                    if isinstance(entry, str):
                        items.append(TextContent(text=entry))
                    else:
                        # entry is autogen_core.Image
                        # Convert to base64 and then into bytes for ImageContent
                        b64 = entry.to_base64()
                        img_bytes = base64.b64decode(b64)
                        items.append(
                            ImageContent(
                                data=img_bytes,  # type: ignore
                                data_format="base64",  # type: ignore
                                mime_type="image/png",  # type: ignore
                            )
                        )

            case "StopMessage":
                assert isinstance(chat_message, StopMessage)
                items.append(TextContent(text=chat_message.content))

            case "HandoffMessage":
                assert isinstance(chat_message, HandoffMessage)
                # Store handoff details as text
                text = f"Handoff target: {chat_message.target}\n\n{chat_message.content}"
                items.append(TextContent(text=text))

            case "ToolCallSummaryMessage":
                assert isinstance(chat_message, ToolCallSummaryMessage)
                items.append(TextContent(text=chat_message.content))

        return ChatMessageContent(role=role, items=items, metadata=metadata, name=chat_message.source)  # type: ignore
