import asyncio
from asyncio import Future

from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.types import PublishNow, RespondNow, TextMessage, ToolApprovalRequest, ToolApprovalResponse
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentRuntime, CancellationToken
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Button, Footer, Header, Input, Markdown, Static


class UserMessage(Markdown):
    def on_mount(self) -> None:
        self.styles.margin = 1
        self.styles.padding = 1
        self.styles.border = ("solid", "green")


class AssistantMessage(Markdown):
    def on_mount(self) -> None:
        self.styles.margin = 1
        self.styles.padding = 1
        self.styles.border = ("solid", "blue")


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

    def __init__(self, runtime: AgentRuntime, welcoming_notice: str, user_name: str) -> None:  # type: ignore
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
        chat_messages = self.query_one("#chat-messages")
        notice = WelcomeMessage(self._welcoming_notice, id="welcome")
        chat_messages.mount(notice)

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
        await self._runtime.publish_message(TextMessage(source=self._user_name, content=user_input))

    async def post_runtime_message(self, message: TextMessage) -> None:  # type: ignore
        """Post a message from the agent runtime to the message list."""
        chat_messages = self.query_one("#chat-messages")
        msg = AssistantMessage(f"{message.source}: {message.content}")
        chat_messages.mount(msg)
        msg.scroll_visible()

    async def handle_tool_approval_request(self, message: ToolApprovalRequest) -> ToolApprovalResponse:  # type: ignore
        chat_messages = self.query_one("#chat-messages")
        future: Future[ToolApprovalResponse] = asyncio.get_event_loop().create_future()
        tool_call_approval_notice = ToolApprovalRequestNotice(message, future)
        chat_messages.mount(tool_call_approval_notice)
        tool_call_approval_notice.scroll_visible()
        return await future


class TextualUserAgent(TypeRoutedAgent):  # type: ignore
    """An agent that is used to receive messages from the runtime."""

    def __init__(self, name: str, description: str, runtime: AgentRuntime, app: TextualChatApp) -> None:  # type: ignore
        super().__init__(name, description, runtime)
        self._app = app

    @message_handler  # type: ignore
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:  # type: ignore
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


async def start_runtime(runtime: SingleThreadedAgentRuntime) -> None:  # type: ignore
    """Run the runtime in a loop."""
    while True:
        await runtime.process_next()
