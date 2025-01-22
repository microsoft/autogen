from collections.abc import AsyncGenerator
from typing import Optional, Sequence

from autogen_agentchat.agents._base_chat_agent import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage, TextMessage
from autogen_core import CancellationToken

from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.exceptions import KernelServiceNotFoundError
from semantic_kernel.kernel import Kernel


class SKAssistantAgent(BaseChatAgent):
    """A Semantic Kernel-based Chat Agent using the autogen BaseChatAgent abstractions.

    - Stores conversation internally in a single ChatHistory instance
    - Converts autogen ChatMessage objects to ChatMessageContent for SK
    - Calls the Semantic Kernel chat completion service on each new set of messages.
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
        """
        Args:
            name: The name of the agent.
            description: A description of the agent's purpose or capabilities.
            kernel: The Semantic Kernel instance to use for chat completions.
            service_id: The ID of the chat completion service. Defaults to "default".
            instructions: Optional system instructions for the assistant.
            execution_settings: Optional prompt execution settings.
        """
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
            sk_msg = ChatMessageContent(role=AuthorRole.USER, content=msg.content, name=msg.source)
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
            or chat_completion_service.instantiate_prompt_execution_settings(
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

        # 5) Add the new assistant message into our chat history
        if assistant_reply.strip():
            self._chat_history.add_message(
                ChatMessageContent(role=AuthorRole.ASSISTANT, content=assistant_reply, name=self.name)
            )

        # 6) Return an autogen Response containing the text
        return Response(chat_message=TextMessage(content=assistant_reply, source=self.name))

    async def on_messages_stream(
        self,
        messages: Sequence[ChatMessage],
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[ChatMessage | Response, None]:
        """
        Handle new messages in streaming mode, yielding partial text messages
        as we receive them, then yield a final single Response.
        """
        # 1) Convert & store new agent messages
        for msg in messages:
            sk_msg = ChatMessageContent(role=AuthorRole.USER, content=msg.content, name=msg.source)
            self._chat_history.add_message(sk_msg)

        # 2) Retrieve chat completion service
        chat_completion_service = self._kernel.get_service(
            service_id=self._service_id,
            type=ChatCompletionClientBase,
        )
        if not chat_completion_service:
            raise KernelServiceNotFoundError(f"Chat completion service not found with service_id: {self._service_id}")

        settings = (
            self._execution_settings
            or self._kernel.get_prompt_execution_settings_from_service_id(self._service_id)
            or chat_completion_service.instantiate_prompt_execution_settings(
                service_id=self._service_id,
                extension_data={"ai_model_id": chat_completion_service.ai_model_id},
            )
        )

        # 3) Stream the SK response
        accumulated_reply = []
        async for sk_message_list in chat_completion_service.get_streaming_chat_message_contents(
            chat_history=self._chat_history,
            settings=settings,
            kernel=self._kernel,
        ):
            for sk_message in sk_message_list:
                # If it's streaming text, yield partial text as a new TextMessage
                if sk_message.content:
                    partial_text = sk_message.content
                    accumulated_reply.append(partial_text)
                    yield TextMessage(content=partial_text, source=self.name)

        # 4) After streaming ends, save the entire assistant message
        final_text = "".join(accumulated_reply).strip()
        if final_text:
            self._chat_history.add_assistant_message(final_text, name=self.name)

        # 5) Finally, yield the single autogen Response
        yield Response(chat_message=TextMessage(content=final_text, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Clear the entire conversation history."""
        self._chat_history.messages.clear()
