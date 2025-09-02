# Compatibility shim for OpenAI SDK type location changes used by transitive deps (e.g., fnllm)
try:
    from typing import Any, cast

    from openai.types.chat import (
        chat_completion_message_function_tool_call as _func_mod,
    )
    from openai.types.chat import (
        chat_completion_message_tool_call as _tool_mod,
    )
    from openai.types.chat import (
        chat_completion_message_tool_call_param as _tool_param_mod,
    )

    _func_mod_any = cast(Any, _func_mod)
    _tool_mod_any = cast(Any, _tool_mod)
    _tool_param_mod_any = cast(Any, _tool_param_mod)

    # Ensure Function exists on the tool_call module
    if not hasattr(_tool_mod_any, "Function") and hasattr(_func_mod_any, "Function"):
        _tool_mod_any.Function = _func_mod_any.Function  # pyright: ignore[reportAttributeAccessIssue]
    # Ensure Function exists on the tool_call_param module (some libs import from here)
    if not hasattr(_tool_param_mod_any, "Function") and hasattr(_func_mod_any, "Function"):
        _tool_param_mod_any.Function = _func_mod_any.Function  # pyright: ignore[reportAttributeAccessIssue]
except Exception:
    # Best-effort shim; safe to ignore if modules are unavailable
    pass

from ._config import (
    GlobalContextConfig,
    GlobalDataConfig,
    LocalContextConfig,
    LocalDataConfig,
    MapReduceConfig,
    SearchConfig,
)
from ._global_search import GlobalSearchTool, GlobalSearchToolArgs, GlobalSearchToolReturn
from ._local_search import LocalSearchTool, LocalSearchToolArgs, LocalSearchToolReturn

__all__ = [
    "GlobalSearchTool",
    "LocalSearchTool",
    "GlobalDataConfig",
    "LocalDataConfig",
    "GlobalContextConfig",
    "GlobalSearchToolArgs",
    "GlobalSearchToolReturn",
    "LocalContextConfig",
    "LocalSearchToolArgs",
    "LocalSearchToolReturn",
    "MapReduceConfig",
    "SearchConfig",
]
