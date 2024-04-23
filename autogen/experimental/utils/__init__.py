from typing import List, Optional, Union
from typing_extensions import Literal
from autogen.experimental.types import AssistantMessage, FunctionCallMessage, FunctionExecutionResultMessage, LLMMessage, Message, MultiModalMessage, SystemMessage, TextMessage, UserMessage

def convert_content_message_to_assistant_message(message: Union[TextMessage, MultiModalMessage, FunctionCallMessage], handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error") -> Optional[AssistantMessage]:
    match message:
        case TextMessage() | FunctionCallMessage():
            return AssistantMessage(content=message.content, source=message.source)
        case MultiModalMessage():
            if handle_unrepresentable == "error":
                raise ValueError("Cannot represent multimodal message as AssistantMessage")
            elif handle_unrepresentable == "ignore":
                return None
            elif handle_unrepresentable == "try_slice":
                return AssistantMessage(content="".join([x for x in message.content if isinstance(x, str)]), source=message.source)


def convert_content_message_to_user_message(message: Union[TextMessage, MultiModalMessage, FunctionCallMessage], handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error") -> Optional[UserMessage]:
    match message:
        case TextMessage() | MultiModalMessage():
            return UserMessage(content=message.content, source=message.source)
        case FunctionCallMessage():
            if handle_unrepresentable == "error":
                raise ValueError("Cannot represent multimodal message as UserMessage")
            elif handle_unrepresentable == "ignore":
                return None
            elif handle_unrepresentable == "try_slice":
                # TODO: what is a sliced function call?
                raise NotImplementedError("Sliced function calls not yet implemented")


def convert_messages_to_llm_messages(messages: List[Message], self_name: str, handle_unrepresentable: Literal["error", "ignore", "try_slice"] = "error") -> List[LLMMessage]:
    result: List[LLMMessage] = []
    for message in messages:
        match message:
            case SystemMessage() | FunctionExecutionResultMessage():
                result.append(message)
            case TextMessage(_, source) | MultiModalMessage(_, source) | FunctionCallMessage(_, source) if source == self_name:
                converted_message_1 = convert_content_message_to_assistant_message(message, handle_unrepresentable)
                if converted_message_1 is not None:
                    result.append(converted_message_1)
            case TextMessage(_, source) | MultiModalMessage(_, source) | FunctionCallMessage(_, source) if source != self_name:
                converted_message_2 = convert_content_message_to_user_message(message, handle_unrepresentable)
                if converted_message_2 is not None:
                    result.append(converted_message_2)
            case _:
                assert False, "unreachable"

    return result
