from autogen.experimental.chat_history import ChatHistoryReadOnly
from autogen.experimental.termination import TerminationResult

from ..summarizer import ChatSummarizer
from ..types import AssistantMessage, FunctionCallMessage, SystemMessage, UserMessage


class LastMessageSummarizer(ChatSummarizer):
    async def summarize_chat(self, chat_history: ChatHistoryReadOnly, termination_result: TerminationResult) -> str:
        messages = chat_history.messages
        if len(messages) == 0:
            raise ValueError("Cannot summarize an empty chat.")
        last_message = messages[-1]
        if isinstance(last_message, SystemMessage):
            raise ValueError("Cannot summarize a chat that ends with a system message.")
        elif isinstance(last_message, UserMessage):
            if not isinstance(last_message.content, str):
                raise ValueError("Cannot summarize a multimodal message yet.")
            return last_message.content
        elif isinstance(last_message, AssistantMessage):
            if last_message.content is None:
                raise ValueError("Cannot summarize a chat that ends with an assistant message with tool calls.")
            return last_message.content
        elif isinstance(last_message, FunctionCallMessage):
            return "\n".join((tool_message.content for tool_message in last_message.call_results))
        else:
            raise ValueError("Unknown message type encountered.")
