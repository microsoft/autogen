from __future__ import annotations

from typing import Literal, Union, Iterable, Optional, List, Dict, Type
from unittest.mock import patch

import httpx
from openai import NotGiven, NOT_GIVEN, Stream
from openai._models import FinalRequestOptions
from openai._types import Headers, Query, Body, ResponseT
from openai.types import Completion
from pydantic import BaseModel, Field
from typing_extensions import Annotated
import pytest
import autogen
import autogen.agentchat.contrib.nexusravenv2_local_function_calling as Nexus
from autogen import UserProxyAgent

# Requires LiteLLM which supports function calling (though not exactly as OpenAI)
# Running on port 8801 (set in LiteLLM command)
# Run LiteLLM with ollama-chat:
# E.g. $ litellm --model ollama_chat/dolphincoder --port 8801 --debug

# Update to match address for LiteLLM, use "0.0.0.0" if in same environment
network_address = "192.168.0.115"

# LOCAL LOCAL
llm_config = {
    "config_list": [
        {"model": "litellmnotneeded", "api_key": "NotRequired", "base_url": f"http://{network_address}:8801"}],
    "cache_seed": None,
}  ## CRITICAL - ENSURE THERE'S NO CACHING FOR TESTING



from openai._base_client import _StreamT
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
    # mock the value returned by agent.client._clients[0]._oai_client.chat.completions._client._request
    mocker.patch.object(agent, "send", fake_send)
    print(f"\n {repr(agent.client._clients[0]._oai_client.chat.completions._client)} \n *************** {dir(agent.client._clients[0]._oai_client.chat.completions._client)} *************** \n\n")
    return agent


@pytest.fixture
def user_proxy(mocker):
    agent = autogen.UserProxyAgent(
        name="user_proxy",
        # MS updated to search for BAZINGA! to terminate
        is_termination_msg=lambda x: x.get("content", "") and "BAZINGA!" in x.get("content", ""),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=4,
        code_execution_config={"work_dir": "/tmp/coding", "use_docker": False}
    )
    generate_reply = mocker.patch.object(agent, "generate_reply", fake_send)
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


def fake_send(msg2send, recipient, silent=False):
    print(f"Recipient: {recipient}")
    print(f"Messages: {msg2send}")
    print(f"Sender: {silent}")
    return True, "Call: random_word_generator(seed=42, prefix='chase')<bot_end> \nThought: functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word \"${randomWord},\" I will now solve this logic problem.`));"


# print(chatbot.llm_config["tools"])
def test_should_respond_with_a_function_call(user_proxy: UserProxyAgent,
                                             chatbot: Nexus.NexusFunctionCallingAssistant):
    @user_proxy.register_for_execution()
    @chatbot.register_for_llm(description="Currency exchange calculator.")
    def currency_calculator(
            base_amount: Annotated[float, "Amount of currency in base_currency"],
            base_currency: Annotated[CurrencySymbol, "Base currency"] = "USD",
            quote_currency: Annotated[CurrencySymbol, "Quote currency"] = "EUR",
    ) -> str:
        quote_amount = exchange_rate(base_currency, quote_currency) * base_amount
        return f"{format(quote_amount, '.2f')} {quote_currency}"

    # Test that the function map is the function
    assert user_proxy.function_map["currency_calculator"]._origin == currency_calculator

    # chatbot.register_reply(
    #     trigger=[Nexus.NexusFunctionCallingAssistant],
    #     reply_func=fake_nexus_response,
    # )


    res = chatbot.initiate_chat(
        chatbot,
        message="How much is 123.45 EUR in USD?",
        #summary_method="reflection_with_llm",
        clear_history=True,
    )
    print(res)
