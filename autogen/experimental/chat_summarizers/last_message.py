from autogen.experimental.chat_history import ChatHistoryReadOnly
from autogen.experimental.termination import Terminated

from ..summarizer import ChatSummarizer
from ..types import FunctionCallMessage, FunctionExecutionResultMessage, MultiModalMessage, SystemMessage, TextMessage


class LastMessageSummarizer(ChatSummarizer):
    async def summarize_chat(self, chat_history: ChatHistoryReadOnly, termination_result: Terminated) -> str:
        messages = chat_history.messages
        if len(messages) == 0:
            raise ValueError("Cannot summarize an empty chat.")
        last_message = messages[-1]
        match last_message:
            case SystemMessage():
                raise ValueError("Cannot summarize a chat that ends with a system message.")
            case TextMessage(content):
                return content
            case MultiModalMessage():
                raise ValueError("Cannot summarize a multimodal message yet.")
            case FunctionCallMessage():
                raise ValueError("Cannot summarize a chat that ends with an assistant message with tool calls.")
            case FunctionExecutionResultMessage(content):
                return "\n".join((tool_message.content for tool_message in content))
