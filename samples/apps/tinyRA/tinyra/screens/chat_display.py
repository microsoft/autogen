import asyncio
from typing import Dict, Optional

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Markdown, LoadingIndicator

from ..database.database import ChatMessage, User, ChatHistory
from ..messages import SelectedReactiveMessage
from ..widgets.custom_widgets import NamedLoadingIndicator, PlaceholderStatic


class ReactiveMessageWidget(Markdown):
    """
    A reactive markdown widget for displaying assistant messages.
    """

    message = reactive(None)

    def __init__(self, message: ChatMessage, user: User, **kwargs):
        super().__init__(**kwargs)
        self.classes = f"{message.role.lower()}-message message"
        self.user = user  # set user before reactive attributes
        self.message = message

    def on_mount(self) -> None:
        self.set_interval(1, self.update_message)
        chat_display = self.app.query_one(ChatDisplay)
        chat_display.scroll_end()

    async def update_message(self) -> None:
        dbm = self.app.config.db_manager
        new_message = await dbm.get_chat_message(root_id=self.message.root_id, id=self.message.id)

        if new_message is None:
            self.remove()
            return

        self.classes = f"{new_message.role.lower()}-message message"
        self.message = new_message

    def watch_message(self) -> None:
        self.update(self.message2markdown())

    def message2markdown(self) -> str:
        """
        Convert a message to markdown that can be displayed in the chat display.

        Args:
            message: a message

        Returns:
            A markdown string.
        """

        if self.message is None:
            return ""

        role = self.message.role
        if role == "user":
            display_name = self.user.name
        elif role == "assistant":
            display_name = "TinyRA"
        else:
            display_name = "\U0001F4AD" * 3

        display_id = self.message.id

        content = self.message.content

        return f"[{display_id}] {display_name}: {content}"
        # return f"{display_name}: sample"


class ClickableReactiveMessageWidget(ReactiveMessageWidget):

    def on_click(self) -> None:
        self.post_message(SelectedReactiveMessage(self.message))


def message_display_handler(message: ChatMessage, user: User):
    if message.role == "user":
        message_widget = ReactiveMessageWidget(message, user)
    else:
        message_widget = ClickableReactiveMessageWidget(message, user)
    return message_widget


class ChatDisplay(ScrollableContainer):
    """
    A container for displaying the chat history.

    When a new message is detected, it is mounted to the container.
    """

    limit_history = 100
    num_messages = reactive(None, recompose=True)
    chat_history = ChatHistory(0, [])

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_id = root_id

    async def update_history(self) -> None:
        dbm = self.app.config.db_manager
        self.chat_history = await dbm.get_chat_history(self.root_id)
        self.user = await dbm.get_user()
        self.num_messages = len(self.chat_history.messages)

    async def on_mount(self):
        self.set_interval(1, self.update_history)

    def compose(self) -> ComposeResult:

        logger = self.app.logger
        logger.info(f"Composing chat display with {self.num_messages} messages from {self.root_id}")

        if self.num_messages is None:
            yield NamedLoadingIndicator(text="Loading chat history")
            return

        if self.num_messages == 0:
            # yield Markdown("No messages yet.")
            yield PlaceholderStatic("Hi there! There are no messages yet 🦗")
            return

        for message in self.chat_history.messages[-self.limit_history :]:
            widget = message_display_handler(message, self.user)
            yield widget
