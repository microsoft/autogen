import copy
from typing import Any, Callable, Dict, Literal

import pytest
from unittest.mock import patch
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from autogen.agentchat import ConversableAgent, UserProxyAgent


@pytest.fixture
def conversable_agent():
    return ConversableAgent(
        "conversable_agent_0",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
        llm_config=False,
        human_input_mode="NEVER",
    )


def test_trigger():
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


def test_generate_reply_raises_on_messages_and_sender_none(conversable_agent):
    with pytest.raises(AssertionError):
        conversable_agent.generate_reply(messages=None, sender=None)


@pytest.mark.asyncio
async def test_a_generate_reply_raises_on_messages_and_sender_none(conversable_agent):
    with pytest.raises(AssertionError):
        await conversable_agent.a_generate_reply(messages=None, sender=None)


def test_update_function_signature_and_register_functions() -> None:
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        agent = ConversableAgent(name="agent", llm_config={})

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


def get_origin(d: Dict[str, Callable[..., Any]]) -> Dict[str, Callable[..., Any]]:
    return {k: v._origin for k, v in d.items()}


def test_register_for_llm():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        agent3 = ConversableAgent(name="agent3", llm_config={})
        agent2 = ConversableAgent(name="agent2", llm_config={})
        agent1 = ConversableAgent(name="agent1", llm_config={})

        @agent3.register_for_llm()
        @agent2.register_for_llm(name="python")
        @agent1.register_for_llm(description="run cell in ipython and return the execution result.")
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

        @agent3.register_for_llm()
        @agent2.register_for_llm()
        @agent1.register_for_llm(name="sh", description="run a shell script and return the execution result.")
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
        mp.setenv("OPENAI_API_KEY", "mock")
        agent = ConversableAgent(name="agent", llm_config={})

        with pytest.raises(ValueError) as e:

            @agent.register_for_llm()
            def exec_python(cell: Annotated[str, "Valid Python cell to execute."]) -> str:
                pass

        assert e.value.args[0] == "Function description is required, none found."


def test_register_for_llm_without_LLM():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        agent = ConversableAgent(name="agent", llm_config=None)
        agent.llm_config = None
        assert agent.llm_config is None

        with pytest.raises(RuntimeError) as e:

            @agent.register_for_llm(description="run cell in ipython and return the execution result.")
            def exec_python(cell: Annotated[str, "Valid Python cell to execute."]) -> str:
                pass

        assert e.value.args[0] == "LLM config must be setup before registering a function for LLM."


def test_register_for_execution():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        agent = ConversableAgent(name="agent", llm_config={})
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


if __name__ == "__main__":
    # test_trigger()
    # test_context()
    # test_max_consecutive_auto_reply()
    # test_generate_code_execution_reply()
    test_conversable_agent()
