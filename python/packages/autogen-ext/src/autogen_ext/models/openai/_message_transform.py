from typing import Any, Callable, Dict, List, cast, get_args

from autogen_core import (
    FunctionCall,
    Image,
)
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelFamily,
    SystemMessage,
    UserMessage,
)
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from ._transformation import (
    TransformerMap,
    build_conditional_transformer_func,
    build_transformer_func,
    register_transformer,
)
from ._utils import assert_valid_name

EMPTY: Dict[str, Any] = {}


def func_call_to_oai(message: FunctionCall) -> ChatCompletionMessageToolCallParam:
    return ChatCompletionMessageToolCallParam(
        id=message.id,
        function={
            "arguments": message.arguments,
            "name": message.name,
        },
        type="function",
    )


# ===Mini Transformers===
def _assert_valid_name(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    assert_valid_name(message.source)
    return EMPTY


def _set_role(role: str) -> Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]:
    def inner(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"role": role}

    return inner


def _set_name(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    assert_valid_name(message.source)
    return {"name": message.source}


def _set_content_direct(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": message.content}


def _set_prepend_text_content(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    assert isinstance(message.content, str)
    prepend = context.get("prepend_name", False)
    prefix = f"{message.source} said:\n" if prepend else ""
    return {"content": prefix + message.content}


def _set_multimodal_content(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    prepend = context.get("prepend_name", False)
    parts: List[ChatCompletionContentPartParam] = []

    for idx, part in enumerate(message.content):
        if isinstance(part, str):
            # If prepend, Append the name to the first text part
            text = f"{message.source} said:\n" + part if prepend and idx == 0 else part
            parts.append(ChatCompletionContentPartTextParam(type="text", text=text))
        elif isinstance(part, Image):
            # TODO: support url based images
            # TODO: support specifying details
            parts.append(cast(ChatCompletionContentPartImageParam, part.to_openai_format()))
        else:
            raise ValueError(f"Unknown content part: {part}")

    return {"content": parts}


def _set_tool_calls(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message.content, list)
    assert isinstance(message, AssistantMessage)
    return {
        "tool_calls": [func_call_to_oai(x) for x in message.content],
    }


def _set_thought_as_content(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, AssistantMessage)
    return {"content": message.thought}


def _set_thought_as_content_gemini(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, AssistantMessage)
    return {"content": message.thought or " "}


def _set_empty_to_whitespace(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    return {"content": message.content or " "}


# === Base Transformers list ===
base_system_message_transformers: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = [
    _set_content_direct,
    _set_role("system"),
]

base_user_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = [
    _assert_valid_name,
    _set_name,
    _set_role("user"),
]

base_assistant_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = [
    _assert_valid_name,
    _set_name,
    _set_role("assistant"),
]


# === Transformers list ===
system_message_transformers: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_system_message_transformers
)

single_user_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_user_transformer_funcs
    + [
        _set_prepend_text_content,
    ]
)

multimodal_user_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_user_transformer_funcs
    + [
        _set_multimodal_content,
    ]
)

single_assistant_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_assistant_transformer_funcs
    + [
        _set_content_direct,
    ]
)

tools_assistant_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_assistant_transformer_funcs
    + [
        _set_tool_calls,
    ]
)

thought_assistant_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    tools_assistant_transformer_funcs
    + [
        _set_thought_as_content,
    ]
)

thought_assistant_transformer_funcs_gemini: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    tools_assistant_transformer_funcs
    + [
        _set_thought_as_content_gemini,
    ]
)


# === Specific message param functions ===


# === Transformer maps ===
user_transformer_funcs: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_user_transformer_funcs,
    "multimodal": multimodal_user_transformer_funcs,
}
user_transformer_constructors: Dict[str, Callable[..., Any]] = {
    "text": ChatCompletionUserMessageParam,
    "multimodal": ChatCompletionUserMessageParam,
}


def user_condition(message: LLMMessage, context: Dict[str, Any]) -> str:
    if isinstance(message.content, str):
        return "text"
    else:
        return "multimodal"


assistant_transformer_funcs: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_assistant_transformer_funcs,
    "tools": tools_assistant_transformer_funcs,
    "thought": thought_assistant_transformer_funcs,
}
assistant_transformer_constructors: Dict[str, Callable[..., Any]] = {
    "text": ChatCompletionAssistantMessageParam,
    "tools": ChatCompletionAssistantMessageParam,
    "thought": ChatCompletionAssistantMessageParam,
}


def assistant_condition(message: LLMMessage, context: Dict[str, Any]) -> str:
    assert isinstance(message, AssistantMessage)
    if isinstance(message.content, list):
        if message.thought is not None:
            return "thought"
        else:
            return "tools"
    else:
        return "text"


user_transformer_funcs_gemini: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_user_transformer_funcs + [_set_empty_to_whitespace],
    "multimodal": multimodal_user_transformer_funcs + [_set_empty_to_whitespace],
}


assistant_transformer_funcs_gemini: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_assistant_transformer_funcs + [_set_empty_to_whitespace],
    "tools": tools_assistant_transformer_funcs,  # that case, message.content is a list of FunctionCall
    "thought": thought_assistant_transformer_funcs_gemini,  # that case, message.content is a list of FunctionCall
}


user_transformer_funcs_claude: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_user_transformer_funcs + [_set_empty_to_whitespace],
    "multimodal": multimodal_user_transformer_funcs + [_set_empty_to_whitespace],
}


assistant_transformer_funcs_claude: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_assistant_transformer_funcs + [_set_empty_to_whitespace],
    "tools": tools_assistant_transformer_funcs,  # that case, message.content is a list of FunctionCall
    "thought": thought_assistant_transformer_funcs_gemini,  # that case, message.content is a list of FunctionCall
}


def function_execution_result_message(
    message: LLMMessage, context: Dict[str, Any]
) -> list[ChatCompletionToolMessageParam]:
    assert isinstance(message, FunctionExecutionResultMessage)
    return [
        ChatCompletionToolMessageParam(content=x.content, role="tool", tool_call_id=x.call_id) for x in message.content
    ]


# === Transformers ===

__BASE_TRANSFORMER_MAP: TransformerMap = {
    SystemMessage: build_transformer_func(
        funcs=system_message_transformers,
        message_param_func=ChatCompletionSystemMessageParam,
    ),
    UserMessage: build_conditional_transformer_func(
        funcs_map=user_transformer_funcs,
        message_param_func_map=user_transformer_constructors,
        condition_func=user_condition,
    ),
    AssistantMessage: build_conditional_transformer_func(
        funcs_map=assistant_transformer_funcs,
        message_param_func_map=assistant_transformer_constructors,
        condition_func=assistant_condition,
    ),
    FunctionExecutionResultMessage: function_execution_result_message,
}

__GEMINI_TRANSFORMER_MAP: TransformerMap = {
    SystemMessage: build_transformer_func(
        funcs=system_message_transformers + [_set_empty_to_whitespace],
        message_param_func=ChatCompletionSystemMessageParam,
    ),
    UserMessage: build_conditional_transformer_func(
        funcs_map=user_transformer_funcs_gemini,
        message_param_func_map=user_transformer_constructors,
        condition_func=user_condition,
    ),
    AssistantMessage: build_conditional_transformer_func(
        funcs_map=assistant_transformer_funcs_gemini,
        message_param_func_map=assistant_transformer_constructors,
        condition_func=assistant_condition,
    ),
    FunctionExecutionResultMessage: function_execution_result_message,
}

__CLAUDE_TRANSFORMER_MAP: TransformerMap = {
    SystemMessage: build_transformer_func(
        funcs=system_message_transformers + [_set_empty_to_whitespace],
        message_param_func=ChatCompletionSystemMessageParam,
    ),
    UserMessage: build_conditional_transformer_func(
        funcs_map=user_transformer_funcs_claude,
        message_param_func_map=user_transformer_constructors,
        condition_func=user_condition,
    ),
    AssistantMessage: build_conditional_transformer_func(
        funcs_map=assistant_transformer_funcs_claude,
        message_param_func_map=assistant_transformer_constructors,
        condition_func=assistant_condition,
    ),
    FunctionExecutionResultMessage: function_execution_result_message,
}


# set openai models to use the transformer map
total_models = get_args(ModelFamily.ANY)
__openai_models = [model for model in total_models if ModelFamily.is_openai(model)]

__claude_models = [model for model in total_models if ModelFamily.is_claude(model)]

__gemini_models = [model for model in total_models if ModelFamily.is_gemini(model)]

__unknown_models = list(set(total_models) - set(__openai_models) - set(__claude_models) - set(__gemini_models))

for model in __openai_models:
    register_transformer("openai", model, __BASE_TRANSFORMER_MAP)

for model in __claude_models:
    register_transformer("openai", model, __BASE_TRANSFORMER_MAP)

for model in __gemini_models:
    register_transformer("openai", model, __GEMINI_TRANSFORMER_MAP)

for model in __unknown_models:
    register_transformer("openai", model, __BASE_TRANSFORMER_MAP)

register_transformer("openai", "default", __BASE_TRANSFORMER_MAP)
