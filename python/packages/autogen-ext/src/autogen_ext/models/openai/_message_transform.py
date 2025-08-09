"""
# `_message_transform.py` Module-Level Documentation

This document is a markdown-formatted version of the module-level docstring inserted into `_message_transform.py` as part of [PR #6063](https://github.com/microsoft/autogen/pull/6063).

---

## AutoGen Modular Transformer Pipeline

This module implements a modular and extensible message transformation pipeline
for converting `LLMMessage` instances into SDK-specific message formats
(e.g., OpenAI-style `ChatCompletionMessageParam`).

---

### 📌 Background

In previous versions of AutoGen, message adaptation was handled in ad-hoc ways,
scattered across model clients. This led to compatibility bugs and code duplication,
especially when supporting diverse models such as Gemini, Claude, or Anthropic SDKs.

To address this, PR #6063 introduced a unified, composable transformer pipeline
that decouples message transformation logic from model SDK constructors.

---

### 🎯 Key Concepts

- **Transformer Function**:
  Transforms a field (e.g., `content`, `name`, `role`) of an `LLMMessage` into a keyword argument.

- **Transformer Pipeline**:
  A sequence of transformer functions composed using `build_transformer_func`.

- **Transformer Map**:
  A dictionary mapping `LLMMessage` types (System, User, Assistant) to transformers for a specific model.

- **Conditional Transformer**:
  Chooses a pipeline dynamically based on message content or runtime conditions.

---

### 🧪 Example: Basic Flow

```python
from autogen_ext.models.openai._message_transform import get_transformer
from autogen.types import AssistantMessage

llm_message = AssistantMessage(name="a", thought="Let's go!")
transformer = get_transformer("openai", "gpt-4", type(llm_message))
sdk_message = transformer(llm_message, context={})
print(sdk_message)
```

---

### 🧰 Example: Define Transformer Functions

```python
def _set_role(role: str):
    def fn(message, context):
        return {"role": role}

    return fn


def _set_content_from_thought(message, context):
    return {"content": message.thought or " "}


base_user_transformer_funcs = [_set_role("user"), _set_content_from_thought]
```

---

### 🛠️ Example: Build and Register Transformer Map

```python
from autogen_ext.models.utils import build_transformer_func, register_transformer
from openai.types.chat import ChatCompletionUserMessageParam
from autogen.types import UserMessage, SystemMessage, AssistantMessage

user_transformer = build_transformer_func(
    funcs=base_user_transformer_funcs, message_param_func=ChatCompletionUserMessageParam
)

MY_TRANSFORMER_MAP = {UserMessage: user_transformer, SystemMessage: ..., AssistantMessage: ...}

register_transformer("openai", "mistral-7b", MY_TRANSFORMER_MAP)
```

---

### 🔁 Conditional Transformer Example

```python
from autogen_ext.models.utils import build_conditional_transformer_func


def condition_func(message, context):
    return "multimodal" if isinstance(message.content, dict) else "text"


user_transformers = {
    "text": [_set_content_from_thought],
    "multimodal": [_set_content_from_thought],  # could be different logic
}

message_param_funcs = {
    "text": ChatCompletionUserMessageParam,
    "multimodal": ChatCompletionUserMessageParam,
}

conditional_user_transformer = build_conditional_transformer_func(
    funcs_map=user_transformers,
    message_param_func_map=message_param_funcs,
    condition_func=condition_func,
)
```

---

### 📦 Design Principles

- ✅ DRY and Composable
- ✅ Model-specific overrides without forking entire clients
- ✅ Explicit separation between transformation logic and SDK builders
- ✅ Future extensibility (e.g., Claude, Gemini, Alibaba)

---

### 📎 Reference

- Introduced in: [PR #6063](https://github.com/microsoft/autogen/pull/6063)
"""

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
    LLMMessageContent,
    TransformerMap,
    TrasformerReturnType,
    build_conditional_transformer_func,
    build_transformer_func,
    register_transformer,
)
from ._utils import assert_valid_name

EMPTY: Dict[str, Any] = {}


def func_call_to_oai(message: FunctionCall) -> ChatCompletionMessageToolCallParam:
    return cast(ChatCompletionMessageToolCallParam, {
        "id": message.id,
        "function": {
            "arguments": message.arguments,
            "name": message.name,
        },
        "type": "function",
    })


# ===Mini Transformers===
def _assert_valid_name(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, None]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    assert_valid_name(message.source)
    return EMPTY


def _set_role(role: str) -> Callable[[LLMMessage, Dict[str, Any]], Dict[str, str]]:
    def inner(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, str]:
        return {"role": role}

    return inner


def _set_name(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, Any]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    assert_valid_name(message.source)
    # Check if name should be included in message
    if context.get("include_name_in_message", True):
        return {"name": message.source}
    else:
        return EMPTY


def _set_content_direct(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, LLMMessageContent]:
    return {"content": message.content}


def _set_prepend_text_content(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, str]:
    assert isinstance(message, (UserMessage, AssistantMessage))
    assert isinstance(message.content, str)
    prepend = context.get("prepend_name", False)
    prefix = f"{message.source} said:\n" if prepend else ""
    return {"content": prefix + message.content}


def _set_multimodal_content(
    message: LLMMessage, context: Dict[str, Any]
) -> Dict[str, List[ChatCompletionContentPartParam]]:
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


def _set_tool_calls(
    message: LLMMessage, context: Dict[str, Any]
) -> Dict[str, List[ChatCompletionMessageToolCallParam]]:
    assert isinstance(message.content, list)
    assert isinstance(message, AssistantMessage)
    return {
        "tool_calls": [func_call_to_oai(x) for x in message.content],
    }


def _set_thought_as_content(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, str | None]:
    assert isinstance(message, AssistantMessage)
    return {"content": message.thought}


def _set_thought_as_content_gemini(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, str | None]:
    assert isinstance(message, AssistantMessage)
    return {"content": message.thought or " "}


def _set_empty_to_whitespace(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, LLMMessageContent]:
    return {"content": message.content or " "}


def _set_pass_message_when_whitespace(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, bool]:
    if isinstance(message.content, str) and (message.content.isspace() or not message.content):
        return {"pass_message": True}
    return {}


def _set_null_content_for_tool_calls(message: LLMMessage, context: Dict[str, Any]) -> Dict[str, None]:
    """Set content to null for tool calls without thought. Required by OpenAI API."""
    assert isinstance(message, AssistantMessage)
    return {"content": None}


# === Base Transformers list ===
base_system_message_transformers: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = [
    _set_content_direct,
    _set_role("system"),
]

base_user_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = [
    _assert_valid_name,
    _set_role("user"),
]

base_assistant_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = [
    _assert_valid_name,
    _set_role("assistant"),
]


# === Transformers list ===
system_message_transformers: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_system_message_transformers
)

single_user_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_user_transformer_funcs
    + [
        _set_name,
        _set_prepend_text_content,
    ]
)

multimodal_user_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_user_transformer_funcs
    + [
        _set_name,
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
        _set_null_content_for_tool_calls,
    ]
)

thought_assistant_transformer_funcs: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_assistant_transformer_funcs
    + [
        _set_tool_calls,
        _set_thought_as_content,
    ]
)

thought_assistant_transformer_funcs_gemini: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_assistant_transformer_funcs
    + [
        _set_tool_calls,
        _set_thought_as_content_gemini,
    ]
)


# === Specific message param functions ===
single_user_transformer_funcs_mistral: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_user_transformer_funcs
    + [
        _set_prepend_text_content,
    ]
)

multimodal_user_transformer_funcs_mistral: List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]] = (
    base_user_transformer_funcs
    + [
        _set_multimodal_content,
    ]
)


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
    "multimodal": multimodal_user_transformer_funcs,
}


assistant_transformer_funcs_gemini: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_assistant_transformer_funcs + [_set_empty_to_whitespace],
    "tools": tools_assistant_transformer_funcs,  # that case, message.content is a list of FunctionCall
    "thought": thought_assistant_transformer_funcs_gemini,  # that case, message.content is a list of FunctionCall
}


user_transformer_funcs_claude: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_user_transformer_funcs + [_set_pass_message_when_whitespace],
    "multimodal": multimodal_user_transformer_funcs + [_set_pass_message_when_whitespace],
}


assistant_transformer_funcs_claude: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_assistant_transformer_funcs + [_set_pass_message_when_whitespace],
    "tools": tools_assistant_transformer_funcs,  # that case, message.content is a list of FunctionCall
    "thought": thought_assistant_transformer_funcs_gemini,  # that case, message.content is a list of FunctionCall
}


user_transformer_funcs_mistral: Dict[str, List[Callable[[LLMMessage, Dict[str, Any]], Dict[str, Any]]]] = {
    "text": single_user_transformer_funcs_mistral,
    "multimodal": multimodal_user_transformer_funcs_mistral,
}


def function_execution_result_message(message: LLMMessage, context: Dict[str, Any]) -> TrasformerReturnType:
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

__MISTRAL_TRANSFORMER_MAP: TransformerMap = {
    SystemMessage: build_transformer_func(
        funcs=system_message_transformers + [_set_empty_to_whitespace],
        message_param_func=ChatCompletionSystemMessageParam,
    ),
    UserMessage: build_conditional_transformer_func(
        funcs_map=user_transformer_funcs_mistral,
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


# set openai models to use the transformer map
total_models = get_args(ModelFamily.ANY)
__openai_models = [model for model in total_models if ModelFamily.is_openai(model)]

__claude_models = [model for model in total_models if ModelFamily.is_claude(model)]

__gemini_models = [model for model in total_models if ModelFamily.is_gemini(model)]

__llama_models = [model for model in total_models if ModelFamily.is_llama(model)]

__unknown_models = list(
    set(total_models) - set(__openai_models) - set(__claude_models) - set(__gemini_models) - set(__llama_models)
)
__mistral_models = [model for model in total_models if ModelFamily.is_mistral(model)]

__unknown_models = list(
    set(total_models) - set(__openai_models) - set(__claude_models) - set(__gemini_models) - set(__mistral_models)
)

for model in __openai_models:
    register_transformer("openai", model, __BASE_TRANSFORMER_MAP)

for model in __claude_models:
    register_transformer("openai", model, __CLAUDE_TRANSFORMER_MAP)

for model in __gemini_models:
    register_transformer("openai", model, __GEMINI_TRANSFORMER_MAP)

for model in __llama_models:
    register_transformer("openai", model, __BASE_TRANSFORMER_MAP)

for model in __mistral_models:
    register_transformer("openai", model, __MISTRAL_TRANSFORMER_MAP)

for model in __unknown_models:
    register_transformer("openai", model, __BASE_TRANSFORMER_MAP)

register_transformer("openai", "default", __BASE_TRANSFORMER_MAP)
