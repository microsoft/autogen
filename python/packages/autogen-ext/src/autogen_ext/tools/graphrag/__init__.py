# Compatibility shim for OpenAI SDK type location changes used by transitive deps (e.g., fnllm)
try:
    from openai.types.chat import (
        chat_completion_message_function_tool_call as _func_mod,
    )
    from openai.types.chat import (
        chat_completion_message_tool_call as _tool_mod,
    )
    from openai.types.chat import (
        chat_completion_message_tool_call_param as _tool_param_mod,
    )

    # Ensure Function exists on the tool_call module
    if not hasattr(_tool_mod, "Function") and hasattr(_func_mod, "Function"):
        setattr(_tool_mod, "Function", _func_mod.Function)
    # Ensure Function exists on the tool_call_param module (some libs import from here)
    if not hasattr(_tool_param_mod, "Function") and hasattr(_func_mod, "Function"):
        setattr(_tool_param_mod, "Function", _func_mod.Function)
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
