from typing import Dict

from autogen_core.models import ModelFamily, ModelInfo

# Models with 200k+ downloads (as of Jan 21, 2025), + phi4, deepseek-r1. Capabilities across model sizes are assumed to be the same.
# TODO: fix model family?
# TODO: json_output is True for all models because ollama supports structured output via pydantic. How to handle this situation?
_MODEL_INFO: Dict[str, ModelInfo] = {
    "all-minilm": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "bge-m3": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "codegemma": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "codellama": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "command-r": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "deepseek-coder": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "deepseek-coder-v2": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "deepseek-r1": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.R1,
        "structured_output": True,
    },
    "dolphin-llama3": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "dolphin-mistral": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "dolphin-mixtral": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "gemma": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "gemma2": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama2": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama2-uncensored": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama3": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama3.1": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama3.2": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama3.2-vision": {
        "vision": True,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llama3.3": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llava": {
        "vision": True,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "llava-llama3": {
        "vision": True,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "mistral": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "mistral-nemo": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "mixtral": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "mxbai-embed-large": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "nomic-embed-text": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "orca-mini": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "phi": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "phi3": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "phi3.5": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "phi4": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "qwen": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "qwen2": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "qwen2.5": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "qwen2.5-coder": {
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "snowflake-arctic-embed": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "starcoder2": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "tinyllama": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "wizardlm2": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "yi": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
    "zephyr": {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    },
}

# TODO: the ollama model card for some of these models were incorrect. I made a best effort to get the actual values, but they aren't guaranteed to be correct.
_MODEL_TOKEN_LIMITS: Dict[str, int] = {
    "all-minilm": 256,
    "bge-m3": 8192,
    "codegemma": 8192,
    "codellama": 16384,
    "codellama:70b": 2048,  # seen claims of 4k and 16k tokens, but nothing verified
    "command-r": 131072,
    "deepseek-coder": 16384,
    "deepseek-coder-v2": 131072,  # metadata says 163840
    "deepseek-r1": 131072,
    "dolphin-llama3": 8192,
    "dolphin-llama3:8b-256k": 256000,
    "dolphin-mistral": 32768,
    "dolphin-mixtral:8x22b": 65536,
    "gemma": 8192,
    "gemma2": 8192,
    "llama2": 4096,
    "llama2-uncensored": 2048,
    "llama3": 8192,
    "llama3.1": 131072,
    "llama3.2": 131072,
    "llama3.2-vision": 131072,
    "llama3.3": 131072,
    "llava": 32768,
    "llava:13b": 4096,
    "llava:34b": 4096,
    "llava-llama3": 8192,
    "mistral": 32768,
    "mistral-nemo": 131072,  # metadata says 1024000??
    "mixtral": 32768,
    "mixtral:8x22b": 65536,
    "mxbai-embed-large": 512,
    "nomic-embed-text": 8192,  # metadata says 2048??
    "orca-mini": 2048,
    "orca-mini:7b": 4096,
    "orca-mini:13b": 4096,
    "orca-mini:70b": 4096,
    "phi": 2048,
    "phi3": 131072,
    "phi3.5": 131072,
    "phi4": 16384,
    "qwen": 32768,
    "qwen2": 32768,
    "qwen2.5": 131072,  # metadata says 32768??
    "qwen2.5-coder": 131072,  # metadata says 32768??
    "qwen2.5-coder:0.5b": 32768,
    "qwen2.5-coder:1.5b": 32768,
    "qwen2.5-coder:3b": 32768,
    "snowflake-arctic-embed": 512,
    "starcoder2": 16384,
    "tinyllama": 2048,
    "wizardlm2": 32768,
    "wizardlm2:8x22b": 65536,
    "yi": 4096,
    "zephyr": 32768,
    "zephyr:141b": 65536,
}


def resolve_model_class(model: str) -> str:
    return model.split(":")[0]


def get_info(model: str) -> ModelInfo:
    resolved_model = resolve_model_class(model)
    return _MODEL_INFO[resolved_model]


def get_token_limit(model: str) -> int:
    if model in _MODEL_TOKEN_LIMITS:
        return _MODEL_TOKEN_LIMITS[model]
    else:
        resolved_model = resolve_model_class(model)
        return _MODEL_TOKEN_LIMITS[resolved_model]
