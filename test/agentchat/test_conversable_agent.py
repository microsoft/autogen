#!/usr/bin/env python3 -m pytest

import asyncio
import copy
import inspect
import os
import sys
import time
import unittest
from typing import Any, Callable, Dict, Literal
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
from typing_extensions import Annotated

import autogen
from autogen.agentchat import ConversableAgent, UserProxyAgent
from autogen.agentchat.conversable_agent import register_function
from autogen.exception_utils import InvalidCarryOverType, SenderRequired

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import MOCK_OPEN_AI_API_KEY, reason, skip_openai  # noqa: E402

here = os.path.abspath(os.path.dirname(__file__))

gpt4_config_list = [{"model": "gpt-4"}, {"model": "gpt-4-turbo"}, {"model": "gpt-4-32k"}, {"model": "gpt-4o"}]


@pytest.fixture
def conversable_agent():
    return ConversableAgent(
        "conversable_agent_0",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
        llm_config=False,
        human_input_mode="NEVER",
    )


def test_sync_trigger():
    agent = ConversableAgent("a0", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent1 = ConversableAgent("a1", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent.register_reply(agent1, lambda recipient, messages, sender, config: (True, "hello"))
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello"
    agent.register_reply("a1", lambda recipient, messages, sender, config: (True, "hello a1"))
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello a1"
    agent.register_reply(
        ConversableAgent, lambda recipient, messages, sender, config: (True, "hello conversable agent")
    )
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello conversable agent"
    agent.register_reply(
        lambda sender: sender.name.startswith("a"), lambda recipient, messages, sender, config: (True, "hello a")
    )
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello a"
    agent.register_reply(
        lambda sender: sender.name.startswith("b"), lambda recipient, messages, sender, config: (True, "hello b")
    )
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello a"
    agent.register_reply(
        ["agent2", agent1], lambda recipient, messages, sender, config: (True, "hello agent2 or agent1")
    )
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello agent2 or agent1"
    agent.register_reply(
        ["agent2", "agent3"], lambda recipient, messages, sender, config: (True, "hello agent2 or agent3")
    )
    agent1.initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello agent2 or agent1"
    pytest.raises(ValueError, agent.register_reply, 1, lambda recipient, messages, sender, config: (True, "hi"))
    pytest.raises(ValueError, agent._match_trigger, 1, agent1)


@pytest.mark.asyncio
async def test_async_trigger():
    agent = ConversableAgent("a0", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent1 = ConversableAgent("a1", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    async def a_reply(recipient, messages, sender, config):
        print("hello from a_reply")
        return (True, "hello")

    agent.register_reply(agent1, a_reply)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello"

    async def a_reply_a1(recipient, messages, sender, config):
        print("hello from a_reply_a1")
        return (True, "hello a1")

    agent.register_reply("a1", a_reply_a1)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello a1"

    async def a_reply_conversable_agent(recipient, messages, sender, config):
        print("hello from a_reply_conversable_agent")
        return (True, "hello conversable agent")

    agent.register_reply(ConversableAgent, a_reply_conversable_agent)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello conversable agent"

    async def a_reply_a(recipient, messages, sender, config):
        print("hello from a_reply_a")
        return (True, "hello a")

    agent.register_reply(lambda sender: sender.name.startswith("a"), a_reply_a)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello a"

    async def a_reply_b(recipient, messages, sender, config):
        print("hello from a_reply_b")
        return (True, "hello b")

    agent.register_reply(lambda sender: sender.name.startswith("b"), a_reply_b)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello a"

    async def a_reply_agent2_or_agent1(recipient, messages, sender, config):
        print("hello from a_reply_agent2_or_agent1")
        return (True, "hello agent2 or agent1")

    agent.register_reply(["agent2", agent1], a_reply_agent2_or_agent1)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello agent2 or agent1"

    async def a_reply_agent2_or_agent3(recipient, messages, sender, config):
        print("hello from a_reply_agent2_or_agent3")
        return (True, "hello agent2 or agent3")

    agent.register_reply(["agent2", "agent3"], a_reply_agent2_or_agent3)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello agent2 or agent1"

    with pytest.raises(ValueError):
        agent.register_reply(1, a_reply)

    with pytest.raises(ValueError):
        agent._match_trigger(1, agent1)


def test_async_trigger_in_sync_chat():
    agent = ConversableAgent("a0", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent1 = ConversableAgent("a1", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent2 = ConversableAgent("a2", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    reply_mock = unittest.mock.MagicMock()

    async def a_reply(recipient, messages, sender, config):
        reply_mock()
        print("hello from a_reply")
        return (True, "hello from reply function")

    agent.register_reply(agent1, a_reply)

    with pytest.raises(RuntimeError) as e:
        agent1.initiate_chat(agent, message="hi")

    assert (
        e.value.args[0] == "Async reply functions can only be used with ConversableAgent.a_initiate_chat(). "
        "The following async reply functions are found: a_reply"
    )

    agent2.register_reply(agent1, a_reply, ignore_async_in_sync_chat=True)
    reply_mock.assert_not_called()


@pytest.mark.asyncio
async def test_sync_trigger_in_async_chat():
    agent = ConversableAgent("a0", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent1 = ConversableAgent("a1", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    def a_reply(recipient, messages, sender, config):
        print("hello from a_reply")
        return (True, "hello from reply function")

    agent.register_reply(agent1, a_reply)
    await agent1.a_initiate_chat(agent, message="hi")
    assert agent1.last_message(agent)["content"] == "hello from reply function"


def test_context():
    agent = ConversableAgent("a0", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent1 = ConversableAgent("a1", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    agent1.send(
        {
            "content": "hello {name}",
            "context": {
                "name": "there",
            },
        },
        agent,
    )
    # expect hello {name} to be printed
    agent1.send(
        {
            "content": lambda context: f"hello {context['name']}",
            "context": {
                "name": "there",
            },
        },
        agent,
    )
    # expect hello there to be printed
    agent.llm_config = {"allow_format_str_template": True}
    agent1.send(
        {
            "content": "hello {name}",
            "context": {
                "name": "there",
            },
        },
        agent,
    )
    # expect hello there to be printed


def test_generate_code_execution_reply():
    agent = ConversableAgent(
        "a0", max_consecutive_auto_reply=10, code_execution_config=False, llm_config=False, human_input_mode="NEVER"
    )

    dummy_messages = [
        {
            "content": "no code block",
            "role": "user",
        },
        {
            "content": "no code block",
            "role": "user",
        },
    ]

    code_message = {
        "content": '```python\nprint("hello world")\n```',
        "role": "user",
    }

    # scenario 1: if code_execution_config is not provided, the code execution should return false, none
    assert agent.generate_code_execution_reply(dummy_messages, config=False) == (False, None)

    # scenario 2: if code_execution_config is provided, but no code block is found, the code execution should return false, none
    assert agent.generate_code_execution_reply(dummy_messages, config={}) == (False, None)

    # scenario 3: if code_execution_config is provided, and code block is found, but it's not within the range of last_n_messages, the code execution should return false, none
    assert agent.generate_code_execution_reply([code_message] + dummy_messages, config={"last_n_messages": 1}) == (
        False,
        None,
    )

    # scenario 4: if code_execution_config is provided, and code block is found, and it's within the range of last_n_messages, the code execution should return true, code block
    agent._code_execution_config = {"last_n_messages": 3, "use_docker": False}
    assert agent.generate_code_execution_reply([code_message] + dummy_messages) == (
        True,
        "exitcode: 0 (execution succeeded)\nCode output: \nhello world\n",
    )
    assert agent._code_execution_config["last_n_messages"] == 3

    # scenario 5: if last_n_messages is set to 'auto' and no code is found, then nothing breaks both when an assistant message is and isn't present
    assistant_message_for_auto = {
        "content": "This is me! The assistant!",
        "role": "assistant",
    }

    dummy_messages_for_auto = []
    for i in range(3):
        dummy_messages_for_auto.append(
            {
                "content": "no code block",
                "role": "user",
            }
        )

        # Without an assistant present
        agent._code_execution_config = {"last_n_messages": "auto", "use_docker": False}
        assert agent.generate_code_execution_reply(dummy_messages_for_auto) == (
            False,
            None,
        )

        # With an assistant message present
        agent._code_execution_config = {"last_n_messages": "auto", "use_docker": False}
        assert agent.generate_code_execution_reply([assistant_message_for_auto] + dummy_messages_for_auto) == (
            False,
            None,
        )

    # scenario 6: if last_n_messages is set to 'auto' and code is found, then we execute it correctly
    dummy_messages_for_auto = []
    for i in range(4):
        # Without an assistant present
        agent._code_execution_config = {"last_n_messages": "auto", "use_docker": False}
        assert agent.generate_code_execution_reply([code_message] + dummy_messages_for_auto) == (
            True,
            "exitcode: 0 (execution succeeded)\nCode output: \nhello world\n",
        )

        # With an assistant message present
        agent._code_execution_config = {"last_n_messages": "auto", "use_docker": False}
        assert agent.generate_code_execution_reply(
            [assistant_message_for_auto] + [code_message] + dummy_messages_for_auto
        ) == (
            True,
            "exitcode: 0 (execution succeeded)\nCode output: \nhello world\n",
        )

        dummy_messages_for_auto.append(
            {
                "content": "no code block",
                "role": "user",
            }
        )

    # scenario 7: if last_n_messages is set to 'auto' and code is present, but not before an assistant message, then nothing happens
    agent._code_execution_config = {"last_n_messages": "auto", "use_docker": False}
    assert agent.generate_code_execution_reply(
        [code_message] + [assistant_message_for_auto] + dummy_messages_for_auto
    ) == (
        False,
        None,
    )
    assert agent._code_execution_config["last_n_messages"] == "auto"

    # scenario 8: if last_n_messages is misconfigures, we expect to see an error
    with pytest.raises(ValueError):
        agent._code_execution_config = {"last_n_messages": -1, "use_docker": False}
        agent.generate_code_execution_reply([code_message])

    with pytest.raises(ValueError):
        agent._code_execution_config = {"last_n_messages": "hello world", "use_docker": False}
        agent.generate_code_execution_reply([code_message])


def test_max_consecutive_auto_reply():
    agent = ConversableAgent("a0", max_consecutive_auto_reply=2, llm_config=False, human_input_mode="NEVER")
    agent1 = ConversableAgent("a1", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")
    assert agent.max_consecutive_auto_reply() == agent.max_consecutive_auto_reply(agent1) == 2
    agent.update_max_consecutive_auto_reply(1)
    assert agent.max_consecutive_auto_reply() == agent.max_consecutive_auto_reply(agent1) == 1

    agent1.initiate_chat(agent, message="hello")
    assert agent._consecutive_auto_reply_counter[agent1] == 1
    agent1.initiate_chat(agent, message="hello again")
    # with auto reply because the counter is reset
    assert agent1.last_message(agent)["role"] == "user"
    assert len(agent1.chat_messages[agent]) == 2
    assert len(agent.chat_messages[agent1]) == 2

    assert agent._consecutive_auto_reply_counter[agent1] == 1
    agent1.send(message="bye", recipient=agent)
    # no auto reply
    assert agent1.last_message(agent)["role"] == "assistant"

    agent1.initiate_chat(agent, clear_history=False, message="hi")
    assert len(agent1.chat_messages[agent]) > 2
    assert len(agent.chat_messages[agent1]) > 2

    assert agent1.reply_at_receive[agent] == agent.reply_at_receive[agent1] is True
    agent1.stop_reply_at_receive(agent)
    assert agent1.reply_at_receive[agent] is False and agent.reply_at_receive[agent1] is True


def test_conversable_agent():
    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="ALWAYS")
    dummy_agent_2 = ConversableAgent(name="dummy_agent_2", llm_config=False, human_input_mode="TERMINATE")

    # monkeypatch.setattr(sys, "stdin", StringIO("exit"))
    dummy_agent_1.receive("hello", dummy_agent_2)  # receive a str
    # monkeypatch.setattr(sys, "stdin", StringIO("TERMINATE\n\n"))
    dummy_agent_1.receive(
        {
            "content": "hello {name}",
            "context": {
                "name": "dummy_agent_2",
            },
        },
        dummy_agent_2,
    )  # receive a dict
    assert "context" in dummy_agent_1.chat_messages[dummy_agent_2][-1]
    # receive dict without openai fields to be printed, such as "content", 'function_call'. There should be no error raised.
    pre_len = len(dummy_agent_1.chat_messages[dummy_agent_2])
    with pytest.raises(ValueError):
        dummy_agent_1.receive({"message": "hello"}, dummy_agent_2)
    assert pre_len == len(
        dummy_agent_1.chat_messages[dummy_agent_2]
    ), "When the message is not an valid openai message, it should not be appended to the oai conversation."

    # monkeypatch.setattr(sys, "stdin", StringIO("exit"))
    dummy_agent_1.send("TERMINATE", dummy_agent_2)  # send a str
    # monkeypatch.setattr(sys, "stdin", StringIO("exit"))
    dummy_agent_1.send(
        {
            "content": "TERMINATE",
        },
        dummy_agent_2,
    )  # send a dict

    # send dict with no openai fields
    pre_len = len(dummy_agent_1.chat_messages[dummy_agent_2])
    with pytest.raises(ValueError):
        dummy_agent_1.send({"message": "hello"}, dummy_agent_2)

    assert pre_len == len(
        dummy_agent_1.chat_messages[dummy_agent_2]
    ), "When the message is not a valid openai message, it should not be appended to the oai conversation."

    # update system message
    dummy_agent_1.update_system_message("new system message")
    assert dummy_agent_1.system_message == "new system message"

    dummy_agent_3 = ConversableAgent(name="dummy_agent_3", llm_config=False, human_input_mode="TERMINATE")
    with pytest.raises(KeyError):
        dummy_agent_1.last_message(dummy_agent_3)

    # Check the description field
    assert dummy_agent_1.description != dummy_agent_1.system_message
    assert dummy_agent_2.description == dummy_agent_2.system_message

    dummy_agent_4 = ConversableAgent(
        name="dummy_agent_4",
        system_message="The fourth dummy agent used for testing.",
        llm_config=False,
        human_input_mode="TERMINATE",
    )
    assert dummy_agent_4.description == "The fourth dummy agent used for testing."  # Same as system message

    dummy_agent_5 = ConversableAgent(
        name="dummy_agent_5",
        system_message="",
        description="The fifth dummy agent used for testing.",
        llm_config=False,
        human_input_mode="TERMINATE",
    )
    assert dummy_agent_5.description == "The fifth dummy agent used for testing."  # Same as system message


def test_generate_reply():
    def add_num(num_to_be_added):
        given_num = 10
        return num_to_be_added + given_num

    dummy_agent_2 = ConversableAgent(
        name="user_proxy", llm_config=False, human_input_mode="TERMINATE", function_map={"add_num": add_num}
    )
    messages = [{"function_call": {"name": "add_num", "arguments": '{ "num_to_be_added": 5 }'}, "role": "assistant"}]

    # when sender is None, messages is provided
    assert (
        dummy_agent_2.generate_reply(messages=messages, sender=None)["content"] == "15"
    ), "generate_reply not working when sender is None"

    # when sender is provided, messages is None
    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="ALWAYS")
    dummy_agent_2._oai_messages[dummy_agent_1] = messages
    assert (
        dummy_agent_2.generate_reply(messages=None, sender=dummy_agent_1)["content"] == "15"
    ), "generate_reply not working when messages is None"

    dummy_agent_2.register_reply(["str", None], ConversableAgent.generate_oai_reply)
    with pytest.raises(SenderRequired):
        dummy_agent_2.generate_reply(messages=messages, sender=None)


def test_generate_reply_raises_on_messages_and_sender_none(conversable_agent):
    with pytest.raises(AssertionError):
        conversable_agent.generate_reply(messages=None, sender=None)


@pytest.mark.asyncio
async def test_a_generate_reply_raises_on_messages_and_sender_none(conversable_agent):
    with pytest.raises(AssertionError):
        await conversable_agent.a_generate_reply(messages=None, sender=None)


def test_generate_reply_with_messages_and_sender_none(conversable_agent):
    messages = [{"role": "user", "content": "hello"}]
    try:
        response = conversable_agent.generate_reply(messages=messages, sender=None)
        assert response is not None, "Response should not be None"
    except AssertionError as e:
        pytest.fail(f"Unexpected AssertionError: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


@pytest.mark.asyncio
async def test_a_generate_reply_with_messages_and_sender_none(conversable_agent):
    messages = [{"role": "user", "content": "hello"}]
    try:
        response = await conversable_agent.a_generate_reply(messages=messages, sender=None)
        assert response is not None, "Response should not be None"
    except AssertionError as e:
        pytest.fail(f"Unexpected AssertionError: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_update_function_signature_and_register_functions() -> None:
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
        agent = ConversableAgent(name="agent", llm_config={"config_list": gpt4_config_list})

        def exec_python(cell: str) -> None:
            pass

        def exec_sh(script: str) -> None:
            pass

        agent.update_function_signature(
            {
                "name": "python",
                "description": "run cell in ipython and return the execution result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cell": {
                            "type": "string",
                            "description": "Valid Python cell to execute.",
                        }
                    },
                    "required": ["cell"],
                },
            },
            is_remove=False,
        )

        functions = agent.llm_config["functions"]
        assert {f["name"] for f in functions} == {"python"}

        agent.update_function_signature(
            {
                "name": "sh",
                "description": "run a shell script and return the execution result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Valid shell script to execute.",
                        }
                    },
                    "required": ["script"],
                },
            },
            is_remove=False,
        )

        functions = agent.llm_config["functions"]
        assert {f["name"] for f in functions} == {"python", "sh"}

        # register the functions
        agent.register_function(
            function_map={
                "python": exec_python,
                "sh": exec_sh,
            }
        )
        assert set(agent.function_map.keys()) == {"python", "sh"}
        assert agent.function_map["python"] == exec_python
        assert agent.function_map["sh"] == exec_sh

        # remove the functions
        agent.register_function(
            function_map={
                "python": None,
            }
        )

        assert set(agent.function_map.keys()) == {"sh"}
        assert agent.function_map["sh"] == exec_sh


def test__wrap_function_sync():
    CurrencySymbol = Literal["USD", "EUR"]

    class Currency(BaseModel):
        currency: Annotated[CurrencySymbol, Field(..., description="Currency code")]
        amount: Annotated[float, Field(100.0, description="Amount of money in the currency")]

    Currency(currency="USD", amount=100.0)

    def exchange_rate(base_currency: CurrencySymbol, quote_currency: CurrencySymbol) -> float:
        if base_currency == quote_currency:
            return 1.0
        elif base_currency == "USD" and quote_currency == "EUR":
            return 1 / 1.1
        elif base_currency == "EUR" and quote_currency == "USD":
            return 1.1
        else:
            raise ValueError(f"Unknown currencies {base_currency}, {quote_currency}")

    agent = ConversableAgent(name="agent", llm_config=False)

    @agent._wrap_function
    def currency_calculator(
        base: Annotated[Currency, "Base currency"],
        quote_currency: Annotated[CurrencySymbol, "Quote currency"] = "EUR",
    ) -> Currency:
        quote_amount = exchange_rate(base.currency, quote_currency) * base.amount
        return Currency(amount=quote_amount, currency=quote_currency)

    assert (
        currency_calculator(base={"currency": "USD", "amount": 110.11}, quote_currency="EUR")
        == '{"currency":"EUR","amount":100.1}'
    )

    assert not inspect.iscoroutinefunction(currency_calculator)


@pytest.mark.asyncio
async def test__wrap_function_async():
    CurrencySymbol = Literal["USD", "EUR"]

    class Currency(BaseModel):
        currency: Annotated[CurrencySymbol, Field(..., description="Currency code")]
        amount: Annotated[float, Field(100.0, description="Amount of money in the currency")]

    Currency(currency="USD", amount=100.0)

    def exchange_rate(base_currency: CurrencySymbol, quote_currency: CurrencySymbol) -> float:
        if base_currency == quote_currency:
            return 1.0
        elif base_currency == "USD" and quote_currency == "EUR":
            return 1 / 1.1
        elif base_currency == "EUR" and quote_currency == "USD":
            return 1.1
        else:
            raise ValueError(f"Unknown currencies {base_currency}, {quote_currency}")

    agent = ConversableAgent(name="agent", llm_config=False)

    @agent._wrap_function
    async def currency_calculator(
        base: Annotated[Currency, "Base currency"],
        quote_currency: Annotated[CurrencySymbol, "Quote currency"] = "EUR",
    ) -> Currency:
        quote_amount = exchange_rate(base.currency, quote_currency) * base.amount
        return Currency(amount=quote_amount, currency=quote_currency)

    assert (
        await currency_calculator(base={"currency": "USD", "amount": 110.11}, quote_currency="EUR")
        == '{"currency":"EUR","amount":100.1}'
    )

    assert inspect.iscoroutinefunction(currency_calculator)


def get_origin(d: Dict[str, Callable[..., Any]]) -> Dict[str, Callable[..., Any]]:
    return {k: v._origin for k, v in d.items()}


def test_register_for_llm():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
        agent3 = ConversableAgent(name="agent3", llm_config={"config_list": gpt4_config_list})
        agent2 = ConversableAgent(name="agent2", llm_config={"config_list": gpt4_config_list})
        agent1 = ConversableAgent(name="agent1", llm_config={"config_list": gpt4_config_list})

        @agent3.register_for_llm()
        @agent2.register_for_llm(name="python")
        @agent1.register_for_llm(description="run cell in ipython and return the execution result.")
        def exec_python(cell: Annotated[str, "Valid Python cell to execute."]) -> str:
            pass

        expected1 = [
            {
                "type": "function",
                "function": {
                    "description": "run cell in ipython and return the execution result.",
                    "name": "exec_python",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cell": {
                                "type": "string",
                                "description": "Valid Python cell to execute.",
                            }
                        },
                        "required": ["cell"],
                    },
                },
            }
        ]
        expected2 = copy.deepcopy(expected1)
        expected2[0]["function"]["name"] = "python"
        expected3 = expected2

        assert agent1.llm_config["tools"] == expected1
        assert agent2.llm_config["tools"] == expected2
        assert agent3.llm_config["tools"] == expected3

        @agent3.register_for_llm()
        @agent2.register_for_llm()
        @agent1.register_for_llm(name="sh", description="run a shell script and return the execution result.")
        async def exec_sh(script: Annotated[str, "Valid shell script to execute."]) -> str:
            pass

        expected1 = expected1 + [
            {
                "type": "function",
                "function": {
                    "name": "sh",
                    "description": "run a shell script and return the execution result.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script": {
                                "type": "string",
                                "description": "Valid shell script to execute.",
                            }
                        },
                        "required": ["script"],
                    },
                },
            }
        ]
        expected2 = expected2 + [expected1[1]]
        expected3 = expected3 + [expected1[1]]

        assert agent1.llm_config["tools"] == expected1
        assert agent2.llm_config["tools"] == expected2
        assert agent3.llm_config["tools"] == expected3


def test_register_for_llm_api_style_function():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
        agent3 = ConversableAgent(name="agent3", llm_config={"config_list": gpt4_config_list})
        agent2 = ConversableAgent(name="agent2", llm_config={"config_list": gpt4_config_list})
        agent1 = ConversableAgent(name="agent1", llm_config={"config_list": gpt4_config_list})

        @agent3.register_for_llm(api_style="function")
        @agent2.register_for_llm(name="python", api_style="function")
        @agent1.register_for_llm(
            description="run cell in ipython and return the execution result.", api_style="function"
        )
        def exec_python(cell: Annotated[str, "Valid Python cell to execute."]) -> str:
            pass

        expected1 = [
            {
                "description": "run cell in ipython and return the execution result.",
                "name": "exec_python",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cell": {
                            "type": "string",
                            "description": "Valid Python cell to execute.",
                        }
                    },
                    "required": ["cell"],
                },
            }
        ]
        expected2 = copy.deepcopy(expected1)
        expected2[0]["name"] = "python"
        expected3 = expected2

        assert agent1.llm_config["functions"] == expected1
        assert agent2.llm_config["functions"] == expected2
        assert agent3.llm_config["functions"] == expected3

        @agent3.register_for_llm(api_style="function")
        @agent2.register_for_llm(api_style="function")
        @agent1.register_for_llm(
            name="sh", description="run a shell script and return the execution result.", api_style="function"
        )
        async def exec_sh(script: Annotated[str, "Valid shell script to execute."]) -> str:
            pass

        expected1 = expected1 + [
            {
                "name": "sh",
                "description": "run a shell script and return the execution result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Valid shell script to execute.",
                        }
                    },
                    "required": ["script"],
                },
            }
        ]
        expected2 = expected2 + [expected1[1]]
        expected3 = expected3 + [expected1[1]]

        assert agent1.llm_config["functions"] == expected1
        assert agent2.llm_config["functions"] == expected2
        assert agent3.llm_config["functions"] == expected3


def test_register_for_llm_without_description():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
        agent = ConversableAgent(name="agent", llm_config={"config_list": gpt4_config_list})

        with pytest.raises(ValueError) as e:

            @agent.register_for_llm()
            def exec_python(cell: Annotated[str, "Valid Python cell to execute."]) -> str:
                pass

        assert e.value.args[0] == "Function description is required, none found."


def test_register_for_llm_without_LLM():
    agent = ConversableAgent(name="agent", llm_config=None)
    with pytest.raises(
        AssertionError,
        match="To update a tool signature, agent must have an llm_config",
    ):

        @agent.register_for_llm(description="do things.")
        def do_stuff(s: str) -> str:
            return f"{s} done"


def test_register_for_llm_without_configuration():
    with pytest.raises(
        ValueError,
        match="When using OpenAI or Azure OpenAI endpoints, specify a non-empty 'model' either in 'llm_config' or in each config of 'config_list'.",
    ):
        ConversableAgent(name="agent", llm_config={"config_list": []})


def test_register_for_llm_without_model_name():
    with pytest.raises(
        ValueError,
        match="When using OpenAI or Azure OpenAI endpoints, specify a non-empty 'model' either in 'llm_config' or in each config of 'config_list'.",
    ):
        ConversableAgent(name="agent", llm_config={"config_list": [{"model": ""}]})


def test_register_for_execution():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
        agent = ConversableAgent(name="agent", llm_config={"config_list": [{"model": "gpt-4"}]})
        user_proxy_1 = UserProxyAgent(name="user_proxy_1")
        user_proxy_2 = UserProxyAgent(name="user_proxy_2")

        @user_proxy_2.register_for_execution(name="python")
        @agent.register_for_execution()
        @agent.register_for_llm(description="run cell in ipython and return the execution result.")
        @user_proxy_1.register_for_execution()
        def exec_python(cell: Annotated[str, "Valid Python cell to execute."]):
            pass

        expected_function_map_1 = {"exec_python": exec_python}
        assert get_origin(agent.function_map) == expected_function_map_1
        assert get_origin(user_proxy_1.function_map) == expected_function_map_1

        expected_function_map_2 = {"python": exec_python}
        assert get_origin(user_proxy_2.function_map) == expected_function_map_2

        @agent.register_for_execution()
        @agent.register_for_llm(description="run a shell script and return the execution result.")
        @user_proxy_1.register_for_execution(name="sh")
        async def exec_sh(script: Annotated[str, "Valid shell script to execute."]):
            pass

        expected_function_map = {
            "exec_python": exec_python,
            "sh": exec_sh,
        }
        assert get_origin(agent.function_map) == expected_function_map
        assert get_origin(user_proxy_1.function_map) == expected_function_map


def test_register_functions():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
        agent = ConversableAgent(name="agent", llm_config={"config_list": gpt4_config_list})
        user_proxy = UserProxyAgent(name="user_proxy")

        def exec_python(cell: Annotated[str, "Valid Python cell to execute."]) -> str:
            pass

        register_function(
            exec_python,
            caller=agent,
            executor=user_proxy,
            description="run cell in ipython and return the execution result.",
        )

        expected_function_map = {"exec_python": exec_python}
        assert get_origin(user_proxy.function_map) == expected_function_map

        expected = [
            {
                "type": "function",
                "function": {
                    "description": "run cell in ipython and return the execution result.",
                    "name": "exec_python",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cell": {
                                "type": "string",
                                "description": "Valid Python cell to execute.",
                            }
                        },
                        "required": ["cell"],
                    },
                },
            }
        ]
        assert agent.llm_config["tools"] == expected


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_function_registration_e2e_sync() -> None:
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "tags": ["tool"],
        },
        file_location=KEY_LOC,
    )

    llm_config = {
        "config_list": config_list,
    }

    coder = autogen.AssistantAgent(
        name="chatbot",
        system_message="For coding tasks, only use the functions you have been provided with. Reply TERMINATE when the task is done.",
        llm_config=llm_config,
    )

    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        system_message="A proxy for the user for executing code.",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config={"work_dir": "coding"},
    )

    # define functions according to the function description
    timer_mock = unittest.mock.MagicMock()
    stopwatch_mock = unittest.mock.MagicMock()

    # An example async function registered using decorators
    @user_proxy.register_for_execution()
    @coder.register_for_llm(description="create a timer for N seconds")
    def timer(num_seconds: Annotated[str, "Number of seconds in the timer."]) -> str:
        print("timer is running")
        for i in range(int(num_seconds)):
            print(".", end="")
            time.sleep(0.01)
        print()

        timer_mock(num_seconds=num_seconds)
        return "Timer is done!"

    # An example sync function registered using register_function
    def stopwatch(num_seconds: Annotated[str, "Number of seconds in the stopwatch."]) -> str:
        print("stopwatch is running")
        # assert False, "stopwatch's alive!"
        for i in range(int(num_seconds)):
            print(".", end="")
            time.sleep(0.01)
        print()

        stopwatch_mock(num_seconds=num_seconds)
        return "Stopwatch is done!"

    register_function(stopwatch, caller=coder, executor=user_proxy, description="create a stopwatch for N seconds")

    # start the conversation
    # 'await' is used to pause and resume code execution for async IO operations.
    # Without 'await', an async function returns a coroutine object but doesn't execute the function.
    # With 'await', the async function is executed and the current function is paused until the awaited function returns a result.
    user_proxy.initiate_chat(  # noqa: F704
        coder,
        message="Create a timer for 1 second and then a stopwatch for 2 seconds.",
    )

    timer_mock.assert_called_once_with(num_seconds="1")
    stopwatch_mock.assert_called_once_with(num_seconds="2")


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
@pytest.mark.asyncio()
async def test_function_registration_e2e_async() -> None:
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "tags": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
        file_location=KEY_LOC,
    )

    llm_config = {
        "config_list": config_list,
    }

    coder = autogen.AssistantAgent(
        name="chatbot",
        system_message="For coding tasks, only use the functions you have been provided with. Reply TERMINATE when the task is done.",
        llm_config=llm_config,
    )

    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        system_message="A proxy for the user for executing code.",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config={"work_dir": "coding"},
    )

    # define functions according to the function description
    timer_mock = unittest.mock.MagicMock()
    stopwatch_mock = unittest.mock.MagicMock()

    # An example async function registered using register_function
    async def timer(num_seconds: Annotated[str, "Number of seconds in the timer."]) -> str:
        print("timer is running")
        for i in range(int(num_seconds)):
            print(".", end="")
            await asyncio.sleep(0.01)
        print()

        timer_mock(num_seconds=num_seconds)
        return "Timer is done!"

    register_function(timer, caller=coder, executor=user_proxy, description="create a timer for N seconds")

    # An example sync function registered using decorators
    @user_proxy.register_for_execution()
    @coder.register_for_llm(description="create a stopwatch for N seconds")
    def stopwatch(num_seconds: Annotated[str, "Number of seconds in the stopwatch."]) -> str:
        print("stopwatch is running")
        # assert False, "stopwatch's alive!"
        for i in range(int(num_seconds)):
            print(".", end="")
            time.sleep(0.01)
        print()

        stopwatch_mock(num_seconds=num_seconds)
        return "Stopwatch is done!"

    # start the conversation
    # 'await' is used to pause and resume code execution for async IO operations.
    # Without 'await', an async function returns a coroutine object but doesn't execute the function.
    # With 'await', the async function is executed and the current function is paused until the awaited function returns a result.
    await user_proxy.a_initiate_chat(  # noqa: F704
        coder,
        message="Create a timer for 1 second and then a stopwatch for 2 seconds.",
    )

    timer_mock.assert_called_once_with(num_seconds="1")
    stopwatch_mock.assert_called_once_with(num_seconds="2")


@pytest.mark.skipif(skip_openai, reason=reason)
def test_max_turn():
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC, filter_dict={"tags": ["gpt-3.5-turbo"]})

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        max_consecutive_auto_reply=10,
        llm_config={"config_list": config_list},
    )

    user_proxy = autogen.UserProxyAgent(name="user", human_input_mode="ALWAYS", code_execution_config=False)

    # Use MagicMock to create a mock get_human_input function
    user_proxy.get_human_input = MagicMock(return_value="Not funny. Try again.")
    res = user_proxy.initiate_chat(assistant, clear_history=True, max_turns=3, message="Hello, make a joke about AI.")
    print("Result summary:", res.summary)
    print("Human input:", res.human_input)
    print("history", res.chat_history)
    assert len(res.chat_history) <= 6


@pytest.mark.skipif(skip_openai, reason=reason)
def test_message_func():
    import random

    class Function:
        call_count = 0

        def get_random_number(self):
            self.call_count += 1
            return random.randint(0, 100)

    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    def my_message_play(sender, recipient, context):
        final_msg = {}
        final_msg["content"] = "Let's play a game."
        final_msg["function_call"] = {"name": "get_random_number", "arguments": "{}"}
        return final_msg

    func = Function()
    # autogen.ChatCompletion.start_logging()
    user = UserProxyAgent(
        "user",
        code_execution_config={
            "work_dir": here,
            "use_docker": False,
        },
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
    )
    player = autogen.AssistantAgent(
        name="Player",
        system_message="You will use function `get_random_number` to get a random number. Stop only when you get at least 1 even number and 1 odd number. Reply TERMINATE to stop.",
        description="A player that makes function_calls.",
        llm_config={"config_list": config_list},
        function_map={"get_random_number": func.get_random_number},
    )

    chat_res_play = user.initiate_chat(
        player,
        message={"content": "Let's play a game.", "function_call": {"name": "get_random_number", "arguments": "{}"}},
        max_turns=1,
    )
    print(chat_res_play.summary)

    chat_res_play = user.initiate_chat(
        player,
        message=my_message_play,
        max_turns=1,
    )
    print(chat_res_play.summary)


@pytest.mark.skipif(skip_openai, reason=reason)
def test_summary():
    import random

    class Function:
        call_count = 0

        def get_random_number(self):
            self.call_count += 1
            return random.randint(0, 100)

    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"tags": ["gpt-3.5-turbo"]}
    )

    def my_message_play(sender, recipient, context):
        final_msg = {}
        final_msg["content"] = "Let's play a game."
        final_msg["function_call"] = {"name": "get_random_number", "arguments": "{}"}
        return final_msg

    def my_summary(sender, recipient, summary_args):
        prefix = summary_args.get("prefix", "Summary:")
        return prefix + recipient.chat_messages[sender][-1].get("content", "")

    func = Function()
    # autogen.ChatCompletion.start_logging()
    user = UserProxyAgent(
        "user",
        code_execution_config={
            "work_dir": here,
            "use_docker": False,
        },
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
    )
    player = autogen.AssistantAgent(
        name="Player",
        system_message="You will use function `get_random_number` to get a random number. Stop only when you get at least 1 even number and 1 odd number. Reply TERMINATE to stop.",
        description="A player that makes function_calls.",
        llm_config={"config_list": config_list},
        function_map={"get_random_number": func.get_random_number},
    )

    chat_res_play = user.initiate_chat(
        player,
        message=my_message_play,
        # message="Make a joke about AI",
        max_turns=1,
        summary_method="reflection_with_llm",
        summary_args={"summary_prompt": "Summarize the conversation into less than five words."},
    )
    print(chat_res_play.summary)

    chat_res_play = user.initiate_chat(
        player,
        # message=my_message_play,
        message="Make a joke about AI",
        max_turns=1,
        summary_method=my_summary,
        summary_args={"prefix": "This is the last message:"},
    )
    print(chat_res_play.summary)

    chat_res_play = user.initiate_chat(
        player,
        message={"content": "Let's play a game.", "function_call": {"name": "get_random_number", "arguments": "{}"}},
        max_turns=1,
        summary_method=my_summary,
        summary_args={"prefix": "This is the last message:"},
    )
    print(chat_res_play.summary)


def test_process_before_send():
    print_mock = unittest.mock.MagicMock()

    # Updated to include sender parameter
    def send_to_frontend(sender, message, recipient, silent):
        assert sender.name == "dummy_agent_1", "Sender is not the expected agent"
        if not silent:
            print(f"Message sent from {sender.name} to {recipient.name}: {message}")
            print_mock(message=message)
        return message

    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="NEVER")
    dummy_agent_2 = ConversableAgent(name="dummy_agent_2", llm_config=False, human_input_mode="NEVER")
    dummy_agent_1.register_hook("process_message_before_send", send_to_frontend)
    dummy_agent_1.send("hello", dummy_agent_2)
    print_mock.assert_called_once_with(message="hello")
    dummy_agent_1.send("silent hello", dummy_agent_2, silent=True)
    print_mock.assert_called_once_with(message="hello")


def test_messages_with_carryover():
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )
    context = dict(message="hello", carryover="Testing carryover.")
    generated_message = agent1.generate_init_message(**context)
    assert isinstance(generated_message, str)

    context = dict(message="hello", carryover=["Testing carryover.", "This should pass"])
    generated_message = agent1.generate_init_message(**context)
    assert isinstance(generated_message, str)

    context = dict(message="hello", carryover=3)
    with pytest.raises(InvalidCarryOverType):
        agent1.generate_init_message(**context)

    # Test multimodal messages
    mm_content = [
        {"type": "text", "text": "hello"},
        {"type": "text", "text": "goodbye"},
        {
            "type": "image_url",
            "image_url": {"url": "https://example.com/image.png"},
        },
    ]
    mm_message = {"content": mm_content}
    context = dict(
        message=mm_message,
        carryover="Testing carryover.",
    )
    generated_message = agent1.generate_init_message(**context)
    assert isinstance(generated_message, dict)
    assert len(generated_message["content"]) == 4

    context = dict(message=mm_message, carryover=["Testing carryover.", "This should pass"])
    generated_message = agent1.generate_init_message(**context)
    assert isinstance(generated_message, dict)
    assert len(generated_message["content"]) == 4

    context = dict(message=mm_message, carryover=3)
    with pytest.raises(InvalidCarryOverType):
        agent1.generate_init_message(**context)

    # Test without carryover
    print(mm_message)
    context = dict(message=mm_message)
    generated_message = agent1.generate_init_message(**context)
    assert isinstance(generated_message, dict)
    assert len(generated_message["content"]) == 3

    # Test without text in multimodal message
    mm_content = [
        {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}},
    ]
    mm_message = {"content": mm_content}
    context = dict(message=mm_message)
    generated_message = agent1.generate_init_message(**context)
    assert isinstance(generated_message, dict)
    assert len(generated_message["content"]) == 1

    generated_message = agent1.generate_init_message(**context, carryover="Testing carryover.")
    assert isinstance(generated_message, dict)
    assert len(generated_message["content"]) == 2


def test_chat_history():
    alice = autogen.ConversableAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )

    charlie = autogen.ConversableAgent(
        "charlie",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is charlie speaking.",
    )

    max_turns = 2

    def bob_initiate_chat(agent: ConversableAgent, text: Literal["past", "future"]):
        _ = agent.initiate_chat(
            alice,
            message=f"This is bob from the {text} speaking.",
            max_turns=max_turns,
            clear_history=False,
            silent=True,
        )
        _ = agent.initiate_chat(
            charlie,
            message=f"This is bob from the {text} speaking.",
            max_turns=max_turns,
            clear_history=False,
            silent=True,
        )

    bob = autogen.ConversableAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob from the past speaking.",
    )
    bob_initiate_chat(bob, "past")
    context = bob.chat_messages

    del bob

    # Test agent with chat history
    bob = autogen.ConversableAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob from the future speaking.",
        chat_messages=context,
    )

    assert bool(bob.chat_messages)
    assert bob.chat_messages == context

    # two times the max turns due to bob replies
    assert len(bob.chat_messages[alice]) == 2 * max_turns
    assert len(bob.chat_messages[charlie]) == 2 * max_turns

    bob_initiate_chat(bob, "future")
    assert len(bob.chat_messages[alice]) == 4 * max_turns
    assert len(bob.chat_messages[charlie]) == 4 * max_turns

    assert bob.chat_messages[alice][0]["content"] == "This is bob from the past speaking."
    assert bob.chat_messages[charlie][0]["content"] == "This is bob from the past speaking."

    assert bob.chat_messages[alice][-2]["content"] == "This is bob from the future speaking."
    assert bob.chat_messages[charlie][-2]["content"] == "This is bob from the future speaking."


def test_http_client():

    import httpx

    with pytest.raises(TypeError):
        config_list = [
            {
                "model": "my-gpt-4-deployment",
                "api_key": "",
                "http_client": httpx.Client(),
            }
        ]

        autogen.ConversableAgent(
            "test_agent",
            human_input_mode="NEVER",
            llm_config={"config_list": config_list},
            default_auto_reply="This is alice speaking.",
        )


def test_adding_duplicate_function_warning():

    config_base = [{"base_url": "http://0.0.0.0:8000", "api_key": "NULL"}]

    agent = autogen.ConversableAgent(
        "jtoy",
        llm_config={"config_list": config_base},
    )

    def sample_function():
        pass

    agent.register_function(
        function_map={
            "sample_function": sample_function,
        }
    )
    agent.update_function_signature(
        {
            "name": "foo",
        },
        is_remove=False,
    )
    agent.update_tool_signature(
        {
            "type": "function",
            "function": {
                "name": "yo",
            },
        },
        is_remove=False,
    )

    with pytest.warns(UserWarning, match="Function 'sample_function' is being overridden."):
        agent.register_function(
            function_map={
                "sample_function": sample_function,
            }
        )
    with pytest.warns(UserWarning, match="Function 'foo' is being overridden."):
        agent.update_function_signature(
            {
                "name": "foo",
            },
            is_remove=False,
        )
    with pytest.warns(UserWarning, match="Function 'yo' is being overridden."):
        agent.update_tool_signature(
            {
                "type": "function",
                "function": {
                    "name": "yo",
                },
            },
            is_remove=False,
        )


def test_process_gemini_carryover():
    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="NEVER")
    content = "I am your assistant."
    carryover_content = "How can I help you?"
    gemini_kwargs = {"carryover": [{"content": carryover_content}]}
    proc_content = dummy_agent_1._process_carryover(content=content, kwargs=gemini_kwargs)
    assert proc_content == content + "\nContext: \n" + carryover_content, "Incorrect carryover processing"


def test_process_carryover():
    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="NEVER")
    content = "I am your assistant."
    carryover = "How can I help you?"
    kwargs = {"carryover": carryover}
    proc_content = dummy_agent_1._process_carryover(content=content, kwargs=kwargs)
    assert proc_content == content + "\nContext: \n" + carryover, "Incorrect carryover processing"

    carryover_l = ["How can I help you?"]
    kwargs = {"carryover": carryover_l}
    proc_content = dummy_agent_1._process_carryover(content=content, kwargs=kwargs)
    assert proc_content == content + "\nContext: \n" + carryover, "Incorrect carryover processing"

    proc_content_empty_carryover = dummy_agent_1._process_carryover(content=content, kwargs={"carryover": None})
    assert proc_content_empty_carryover == content, "Incorrect carryover processing"


def test_handle_gemini_carryover():
    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="NEVER")
    content = "I am your assistant"
    carryover_content = "How can I help you?"
    gemini_kwargs = {"carryover": [{"content": carryover_content}]}
    proc_content = dummy_agent_1._handle_carryover(message=content, kwargs=gemini_kwargs)
    assert proc_content == content + "\nContext: \n" + carryover_content, "Incorrect carryover processing"


def test_handle_carryover():
    dummy_agent_1 = ConversableAgent(name="dummy_agent_1", llm_config=False, human_input_mode="NEVER")
    content = "I am your assistant."
    carryover = "How can I help you?"
    kwargs = {"carryover": carryover}
    proc_content = dummy_agent_1._handle_carryover(message=content, kwargs=kwargs)
    assert proc_content == content + "\nContext: \n" + carryover, "Incorrect carryover processing"

    carryover_l = ["How can I help you?"]
    kwargs = {"carryover": carryover_l}
    proc_content = dummy_agent_1._handle_carryover(message=content, kwargs=kwargs)
    assert proc_content == content + "\nContext: \n" + carryover, "Incorrect carryover processing"

    proc_content_empty_carryover = dummy_agent_1._handle_carryover(message=content, kwargs={"carryover": None})
    assert proc_content_empty_carryover == content, "Incorrect carryover processing"


if __name__ == "__main__":
    # test_trigger()
    # test_context()
    # test_max_consecutive_auto_reply()
    # test_generate_code_execution_reply()
    # test_conversable_agent()
    # test_no_llm_config()
    # test_max_turn()
    # test_process_before_send()
    # test_message_func()

    test_summary()
    test_adding_duplicate_function_warning()
    # test_function_registration_e2e_sync()

    test_process_gemini_carryover()
    test_process_carryover()
