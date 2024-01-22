import os
import sys
import time

import pytest
import autogen
from autogen.agentchat import AssistantAgent, UserProxyAgent
from autogen.cache import Cache

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai, skip_redis  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip_openai_tests = True
else:
    skip_openai_tests = False or skip_openai

try:
    import redis
except ImportError:
    skip_redis_tests = True
else:
    skip_redis_tests = False or skip_redis


@pytest.mark.skipif(skip_openai_tests, reason="openai not installed OR requested to skip")
def test_legacy_disk_cache():
    random_cache_seed = int.from_bytes(os.urandom(2), "big")
    start_time = time.time()
    cold_cache_messages = run_conversation(
        cache_seed=random_cache_seed,
    )
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_messages = run_conversation(
        cache_seed=random_cache_seed,
    )
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_messages == warm_cache_messages
    assert duration_with_warm_cache < duration_with_cold_cache


@pytest.mark.skipif(skip_openai_tests or skip_redis_tests, reason="redis not installed OR requested to skip")
def test_redis_cache():
    random_cache_seed = int.from_bytes(os.urandom(2), "big")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    start_time = time.time()
    with Cache.redis(random_cache_seed, redis_url) as cache_client:
        cold_cache_messages = run_conversation(cache_seed=None, cache=cache_client)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_messages = run_conversation(cache_seed=None, cache=cache_client)
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_messages == warm_cache_messages
        assert duration_with_warm_cache < duration_with_cold_cache

    random_cache_seed = int.from_bytes(os.urandom(2), "big")
    with Cache.redis(random_cache_seed, redis_url) as cache_client:
        cold_cache_messages = run_groupchat_conversation(cache=cache_client)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_messages = run_groupchat_conversation(cache=cache_client)
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_messages == warm_cache_messages
        assert duration_with_warm_cache < duration_with_cold_cache


@pytest.mark.skipif(skip_openai_tests, reason="openai not installed OR requested to skip")
def test_disk_cache():
    random_cache_seed = int.from_bytes(os.urandom(2), "big")
    start_time = time.time()
    with Cache.disk(random_cache_seed) as cache_client:
        cold_cache_messages = run_conversation(cache_seed=None, cache=cache_client)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_messages = run_conversation(cache_seed=None, cache=cache_client)
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_messages == warm_cache_messages
        assert duration_with_warm_cache < duration_with_cold_cache

    random_cache_seed = int.from_bytes(os.urandom(2), "big")
    with Cache.disk(random_cache_seed) as cache_client:
        cold_cache_messages = run_groupchat_conversation(cache=cache_client)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_messages = run_groupchat_conversation(cache=cache_client)
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_messages == warm_cache_messages
        assert duration_with_warm_cache < duration_with_cold_cache


def run_conversation(cache_seed, human_input_mode="NEVER", max_consecutive_auto_reply=5, cache=None):
    KEY_LOC = "notebook"
    OAI_CONFIG_LIST = "OAI_CONFIG_LIST"
    here = os.path.abspath(os.path.dirname(__file__))
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": {
                "gpt-3.5-turbo",
                "gpt-35-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-16k-0613",
                "gpt-3.5-turbo-0301",
                "chatgpt-35-turbo-0301",
                "gpt-35-turbo-v0301",
                "gpt",
            },
        },
    )
    llm_config = {
        "cache_seed": cache_seed,
        "config_list": config_list,
        "max_tokens": 1024,
    }
    assistant = AssistantAgent(
        "coding_agent",
        llm_config=llm_config,
    )
    user = UserProxyAgent(
        "user",
        human_input_mode=human_input_mode,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        code_execution_config={
            "work_dir": f"{here}/test_agent_scripts",
            "use_docker": "python:3",
            "timeout": 60,
        },
        llm_config=llm_config,
        system_message="""Is code provided but not enclosed in ``` blocks?
    If so, remind that code blocks need to be enclosed in ``` blocks.
    Reply TERMINATE to end the conversation if the task is finished. Don't say appreciation.
    If "Thank you" or "You\'re welcome" are said in the conversation, then say TERMINATE and that is your last message.""",
    )

    user.initiate_chat(assistant, message="TERMINATE", cache=cache)
    # should terminate without sending any message
    assert assistant.last_message()["content"] == assistant.last_message(user)["content"] == "TERMINATE"
    coding_task = "Print hello world to a file called hello.txt"

    # track how long this takes
    user.initiate_chat(assistant, message=coding_task, cache=cache)
    return user.chat_messages[list(user.chat_messages.keys())[-0]]


def run_groupchat_conversation(cache, human_input_mode="NEVER", max_consecutive_auto_reply=5):
    KEY_LOC = "notebook"
    OAI_CONFIG_LIST = "OAI_CONFIG_LIST"
    here = os.path.abspath(os.path.dirname(__file__))
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": {
                "gpt-3.5-turbo",
                "gpt-35-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-16k-0613",
                "gpt-3.5-turbo-0301",
                "chatgpt-35-turbo-0301",
                "gpt-35-turbo-v0301",
                "gpt",
            },
        },
    )
    llm_config = {
        "cache_seed": None,
        "config_list": config_list,
        "max_tokens": 1024,
    }
    assistant = AssistantAgent(
        "coding_agent",
        llm_config=llm_config,
    )

    planner = AssistantAgent(
        "planner",
        llm_config=llm_config,
    )

    user = UserProxyAgent(
        "user",
        human_input_mode=human_input_mode,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        code_execution_config={
            "work_dir": f"{here}/test_agent_scripts",
            "use_docker": "python:3",
            "timeout": 60,
        },
        system_message="""Is code provided but not enclosed in ``` blocks?
    If so, remind that code blocks need to be enclosed in ``` blocks.
    Reply TERMINATE to end the conversation if the task is finished. Don't say appreciation.
    If "Thank you" or "You\'re welcome" are said in the conversation, then say TERMINATE and that is your last message.""",
    )

    group_chat = autogen.GroupChat(
        agents=[planner, assistant, user],
        messages=[],
        max_round=4,
        speaker_selection_method="round_robin",
    )
    manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=llm_config)

    coding_task = "Print hello world to a file called hello.txt"

    user.initiate_chat(manager, message=coding_task, cache=cache)
    return user.chat_messages[list(user.chat_messages.keys())[-0]]
