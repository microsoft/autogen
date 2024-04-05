import asyncio
from typing import Dict

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Markdown

from ..database.database import ChatMessage, User, ChatHistory


class ReactiveMessageWidget(Markdown):
    """
    A reactive markdown widget for displaying assistant messages.
    """

    message = reactive(None)

    class Selected(Message):
        """Assistant message selected message."""

        def __init__(self, chat_msg_id: str) -> None:
            self.msg_id = chat_msg_id
            super().__init__()

    def __init__(self, message: ChatMessage, user: User, **kwargs):
        super().__init__(**kwargs)
        self.classes = f"{message.role.lower()}-message message"
        self.user = user  # set user before reactive attributes
        self.message = message

    def on_mount(self) -> None:
        self.set_interval(1, self.update_message)
        chat_display = self.app.query_one(ChatDisplay)
        chat_display.scroll_end()

    def on_click(self) -> None:
        self.post_message(self.Selected(self.message.id))

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


def message_display_handler(message: ChatMessage, user: User):
    message_widget = ReactiveMessageWidget(message, user)
    return message_widget


class ChatDisplay(ScrollableContainer):
    """
    A container for displaying the chat history.

    When a new message is detected, it is mounted to the container.
    """

    root_id = 0
    limit_history = 100
    chat_history = ChatHistory(0, [])

    async def on_mount(self):
        dbm = self.app.config.db_manager
        self.chat_history = await dbm.get_chat_history(self.root_id)
        self.user = await dbm.get_user()
        logger = self.app.logger
        num_messages = len(self.chat_history.messages)
        logger.info(f"Chat Display fetched {num_messages} messages")

        await self.recompose()

    def compose(self) -> ComposeResult:
        logger = self.app.logger
        num_messages = len(self.chat_history.messages)
        logger.info(f"Composing chat display with {num_messages} messages")
        for message in self.chat_history.messages[-self.limit_history :]:
            widget = message_display_handler(message, self.user)
            yield widget
