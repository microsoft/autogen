import asyncio
import os
import random
import sys
from asyncio import Future

from agnext.components import Image, RoutedAgent, message_handler
from agnext.core import AgentRuntime, CancellationToken
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Button, Footer, Header, Input, Markdown, Static
from textual_imageview.viewer import ImageViewer

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from agnext.core import TopicId
from common.types import (
    MultiModalMessage,
    PublishNow,
    RespondNow,
    TextMessage,
    ToolApprovalRequest,
    ToolApprovalResponse,
)


class ChatAppMessage(Static):
    def __init__(self, message: TextMessage | MultiModalMessage) -> None:  # type: ignore
        self._message = message
        super().__init__()

    def on_mount(self) -> None:
        self.styles.margin = 1
        self.styles.padding = 1
        self.styles.border = ("solid", "blue")

    def compose(self) -> ComposeResult:
        if isinstance(self._message, TextMessage):
            yield Markdown(f"{self._message.source}:")
            yield Markdown(self._message.content)
        else:
            yield Markdown(f"{self._message.source}:")
            for content in self._message.content:
                if isinstance(content, str):
                    yield Markdown(content)
                elif isinstance(content, Image):
                    viewer = ImageViewer(content.image)
                    viewer.styles.min_width = 50
                    viewer.styles.min_height = 50
                    yield viewer


class WelcomeMessage(Static):
    def on_mount(self) -> None:
        self.styles.margin = 1
        self.styles.padding = 1
        self.styles.border = ("solid", "blue")


class ChatInput(Input):
    def on_mount(self) -> None:
        self.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.clear()


class ToolApprovalRequestNotice(Static):
    def __init__(self, request: ToolApprovalRequest, response_future: Future[ToolApprovalResponse]) -> None:  # type: ignore
        self._tool_call = request.tool_call
        self._future = response_future
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static(f"Tool call: {self._tool_call.name}, arguments: {self._tool_call.arguments[:50]}")
        yield Button("Approve", id="approve", variant="warning")
        yield Button("Deny", id="deny", variant="default")

    def on_mount(self) -> None:
        self.styles.margin = 1
        self.styles.padding = 1
        self.styles.border = ("solid", "red")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        assert button_id is not None
        if button_id == "approve":
            self._future.set_result(ToolApprovalResponse(tool_call_id=self._tool_call.id, approved=True, reason=""))
        else:
            self._future.set_result(ToolApprovalResponse(tool_call_id=self._tool_call.id, approved=False, reason=""))
        self.remove()


class TextualChatApp(App):  # type: ignore
    """A Textual app for a chat interface."""

    def __init__(self, runtime: AgentRuntime, welcoming_notice: str | None = None, user_name: str = "User") -> None:  # type: ignore
        self._runtime = runtime
        self._welcoming_notice = welcoming_notice
        self._user_name = user_name
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield ScrollableContainer(id="chat-messages")
        yield ChatInput()

    def on_mount(self) -> None:
        if self._welcoming_notice is not None:
            chat_messages = self.query_one("#chat-messages")
            notice = WelcomeMessage(self._welcoming_notice, id="welcome")
            chat_messages.mount(notice)

    @property
    def welcoming_notice(self) -> str | None:
        return self._welcoming_notice

    @welcoming_notice.setter
    def welcoming_notice(self, value: str) -> None:
        self._welcoming_notice = value

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value
        await self.publish_user_message(user_input)

    async def post_request_user_input_notice(self) -> None:
        chat_messages = self.query_one("#chat-messages")
        notice = Static("Please enter your input.", id="typing")
        chat_messages.mount(notice)
        notice.scroll_visible()

    async def publish_user_message(self, user_input: str) -> None:
        chat_messages = self.query_one("#chat-messages")
        # Remove all typing messages.
        chat_messages.query("#typing").remove()
        # Publish the user message to the runtime.
        await self._runtime.publish_message(
            # TODO fix hard coded topic_id
            TextMessage(source=self._user_name, content=user_input),
            topic_id=TopicId("default", "default"),
        )

    async def post_runtime_message(self, message: TextMessage | MultiModalMessage) -> None:  # type: ignore
        """Post a message from the agent runtime to the message list."""
        chat_messages = self.query_one("#chat-messages")
        msg = ChatAppMessage(message)
        chat_messages.mount(msg)
        msg.scroll_visible()

    async def handle_tool_approval_request(self, message: ToolApprovalRequest) -> ToolApprovalResponse:  # type: ignore
        chat_messages = self.query_one("#chat-messages")
        future: Future[ToolApprovalResponse] = asyncio.get_event_loop().create_future()  # type: ignore
        tool_call_approval_notice = ToolApprovalRequestNotice(message, future)
        chat_messages.mount(tool_call_approval_notice)
        tool_call_approval_notice.scroll_visible()
        return await future


class TextualUserAgent(RoutedAgent):  # type: ignore
    """An agent that is used to receive messages from the runtime."""

    def __init__(self, description: str, app: TextualChatApp) -> None:  # type: ignore
        super().__init__(description)
        self._app = app

    @message_handler  # type: ignore
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        await self._app.post_runtime_message(message)

    @message_handler  # type: ignore
    async def on_multi_modal_message(self, message: MultiModalMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
        # Save the message to file.
        # Generate a ramdom file name.
        for content in message.content:
            if isinstance(content, Image):
                filename = f"{self.metadata['type']}_{message.source}_{random.randbytes(16).hex()}.png"
                content.image.save(filename)
        await self._app.post_runtime_message(message)

    @message_handler  # type: ignore
    async def on_respond_now(self, message: RespondNow, cancellation_token: CancellationToken) -> None:  # type: ignore
        await self._app.post_request_user_input_notice()

    @message_handler  # type: ignore
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:  # type: ignore
        await self._app.post_request_user_input_notice()

    @message_handler  # type: ignore
    async def on_tool_approval_request(
        self, message: ToolApprovalRequest, cancellation_token: CancellationToken
    ) -> ToolApprovalResponse:
        return await self._app.handle_tool_approval_request(message)
