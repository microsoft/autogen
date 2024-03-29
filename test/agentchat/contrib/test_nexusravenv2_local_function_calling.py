from __future__ import annotations

from typing import Literal, Tuple, Optional, Union, Any, List, Dict

import pytest
from typing_extensions import Annotated

import autogen
import autogen.agentchat.contrib.nexusravenv2_local_function_calling as Nexus
from autogen import UserProxyAgent, Agent, ConversableAgent

# Requires LiteLLM which supports function calling (though not exactly as OpenAI)
# Running on port 8801 (set in LiteLLM command)
# Run LiteLLM with ollama-chat:
# E.g. $ litellm --model ollama_chat/dolphincoder --port 8801 --debug

# Update to match address for LiteLLM, use "0.0.0.0" if in same environment
network_address = "192.168.0.115"

# LOCAL LOCAL
llm_config = {
    "config_list": [
        {"model": "litellmnotneeded", "api_key": "NotRequired", "base_url": f"http://{network_address}:8801"}
    ],
    "cache_seed": None,
}  ## CRITICAL - ENSURE THERE'S NO CACHING FOR TESTING


def create_fake_send(user_proxy):
    def fake_send(msg2send, recipient, silent=False):
        print(f"Recipient: {recipient}")
        print(f"Messages: {msg2send}")
        print(f"Sender: {silent}")
        recipient.receive(message=msg2send, sender=user_proxy, request_reply=True)

    return fake_send


def reply_func(
    recipient: ConversableAgent,
    messages: Optional[List[Dict]] = None,
    sender: Optional[Agent] = None,
    config: Optional[Any] = None,
) -> Tuple[bool, Union[str, Dict, None]]:
    return (
        True,
        "Call: random_word_generator(seed=42, prefix='chase')<bot_end> \nThought: functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word \"${randomWord},\" I will now solve this logic problem.`));",
    )


@pytest.fixture
def chatbot(mocker):
    agent = Nexus.NexusFunctionCallingAssistant(
        name="chatbot",
        system_message="""For currency exchange tasks,
        only use the functions you have been provided with.
        Output 'BAZINGA!' when an answer has been provided.
        Do not include the function name or result in the JSON.
        Example of the return JSON is:
        {
            "parameter_1_name": 100.00,
            "parameter_2_name": "ABC",
            "parameter_3_name": "DEF",
        }.
        Another example of the return JSON is:
        {
            "parameter_1_name": "GHI",
            "parameter_2_name": "ABC",
            "parameter_3_name": "DEF",
            "parameter_4_name": 123.00,
        }. """,  # MS - this was needed to ensure the function name was returned
        llm_config=llm_config,
    )
    agent.register_reply(
        trigger=lambda _: True,
        reply_func=reply_func,
    )

    return agent


@pytest.fixture
def user_proxy(mocker):
    agent = autogen.UserProxyAgent(
        name="user_proxy",
        # MS updated to search for BAZINGA! to terminate
        is_termination_msg=lambda x: x.get("content", "") and "BAZINGA!" in x.get("content", ""),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=4,
        code_execution_config={"work_dir": "/tmp/coding", "use_docker": False},
    )
    mocker.patch.object(agent, "send", create_fake_send(agent))
    return agent


CurrencySymbol = Literal["USD", "EUR"]


def exchange_rate(base_currency: CurrencySymbol, quote_currency: CurrencySymbol) -> float:
    if base_currency == quote_currency:
        return 1.0
    elif base_currency == "USD" and quote_currency == "EUR":
        return 1 / 1.1
    elif base_currency == "EUR" and quote_currency == "USD":
        return 1.1
    else:
        raise ValueError(f"Unknown currencies {base_currency}, {quote_currency}")


# print(chatbot.llm_config["tools"])
def test_should_respond_with_a_function_call(user_proxy: UserProxyAgent, chatbot: Nexus.NexusFunctionCallingAssistant):
    @user_proxy.register_for_execution()
    @chatbot.register_for_llm(description="A Random Word Generator")
    def random_word_generator(
        seed: Annotated[int, "Randomizing Seed for the word generation"] = 42,
        prefix: Annotated[str, "Prefix to Append to the Word that was generated."] = "USD",
    ) -> str:
        return f"{prefix}_not_random_actually_but_this_is_a_test"

    # Test that the function map is the function
    assert user_proxy.function_map["random_word_generator"]._origin == random_word_generator

    user_proxy.initiate_chat(
        chatbot,
        message="Generate Me a Random Word Please",
        summary_method="last_msg",
        # clear_history=True,
    )


def test_parse_function_details():
    input_string = "Call: random_word_generator(seed=42, prefix='chase')<bot_end> \nThought: functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word \"${randomWord},\" I will now solve this logic problem.`));"
    assert Nexus.NexusFunctionCallingAssistant.parse_function_details(input_string) == (
        "random_word_generator",
        {"seed": 42, "prefix": "chase"},
        'functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word "${randomWord}," I will now solve this logic problem.`));',
    )
