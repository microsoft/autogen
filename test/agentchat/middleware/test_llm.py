import pytest
import autogen
from autogen.agentchat.middleware.llm import LLMMiddleware
from conftest import skip_openai

try:
    import openai
except ImportError:
    skip = True
else:
    skip = False or skip_openai

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"

_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                },
                "required": ["location", "format"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_n_day_weather_forecast",
            "description": "Get an N-day weather forecast",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                    "num_days": {
                        "type": "integer",
                        "description": "The number of days to forecast",
                    },
                },
                "required": ["location", "format", "num_days"],
            },
        },
    },
]


@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
def test_llm() -> None:
    config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
    }
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")
    messages = [{"role": "user", "content": "1+1="}]
    reply = mw.call(messages=messages)
    assert "2" in reply


@pytest.mark.asyncio()
@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
async def test_llm_async() -> None:
    config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
    }
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")
    messages = [{"role": "user", "content": "1+1="}]
    reply = await mw.a_call(messages=messages)
    assert "2" in reply


@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
def test_llm_tool_calls() -> None:
    config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
    }
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")
    for tool in _tools:
        mw.update_tool_signature(tool, is_remove=None)

    messages = [{"role": "user", "content": "What's the current weather in New York?"}]
    reply = mw.call(messages=messages)
    assert reply["tool_calls"][0]["function"]["name"] == "get_current_weather"

    messages = [{"role": "user", "content": "What's the weather in New York for the next 5 days?"}]
    reply = mw.call(messages=messages)
    function_names = [tool["function"]["name"] for tool in reply["tool_calls"]]
    assert "get_n_day_weather_forecast" in function_names


@pytest.mark.skipif(skip, reason="openai not installed or requested to skip")
def test_llm_tool_calls_parallel() -> None:
    config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo-1106", "gpt-35-turbo-1106"]},
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
    }
    mw = LLMMiddleware(name="assistant", llm_config=llm_config, system_message="You are a helpful assistant.")
    for tool in _tools:
        mw.update_tool_signature(tool, is_remove=None)

    messages = [{"role": "user", "content": "What's the current weather in New York and San Francisco?"}]
    reply = mw.call(messages=messages)
    print(reply)
    assert len(reply["tool_calls"]) == 2
    assert reply["tool_calls"][0]["function"]["name"] == "get_current_weather"
    assert reply["tool_calls"][1]["function"]["name"] == "get_current_weather"
