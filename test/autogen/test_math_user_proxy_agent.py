from flaml import oai
from flaml.autogen.agent.math_user_proxy_agent import MathUserProxyAgent, _remove_print, _add_print_to_last_line
import pytest
import sys

KEY_LOC = "test/autogen"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows",
)
def test_math_user_proxy_agent():
    try:
        import openai
    except ImportError:
        return

    from flaml.autogen.agent.assistant_agent import AssistantAgent

    conversations = {}
    oai.ChatCompletion.start_logging(conversations)

    config_list = oai.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": ["gpt-4", "gpt4", "gpt-4-32k", "gpt-4-32k-0314"],
        },
    )
    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        oai_config={
            "request_timeout": 600,
            "seed": 42,
            "config_list": config_list,
        },
    )

    mathproxyagent = MathUserProxyAgent(name="MathChatAgent", human_input_mode="NEVER")
    assistant.reset()

    math_problem = "$x^3=125$. What is x?"
    assistant.receive(
        message=mathproxyagent.generate_init_message(math_problem),
        sender=mathproxyagent,
    )
    print(conversations)


def test_add_remove_print():
    # test add print
    code = "a = 4\nb = 5\na,b"
    assert _add_print_to_last_line(code) == "a = 4\nb = 5\nprint(a,b)"

    # test remove print
    code = """print("hello")\na = 4*5\nprint("wolrld")"""
    assert _remove_print(code) == "a = 4*5"

    # test remove print. Only remove prints without indentation
    code = "if 4 > 5:\n\tprint('True')"
    assert _remove_print(code) == code


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows",
)
def test_execute_one_python_code():
    mathproxyagent = MathUserProxyAgent(name="MathChatAgent", human_input_mode="NEVER")

    # no output found 1
    code = "x=3"
    assert mathproxyagent.execute_one_python_code(code)[0] == "No output found. Make sure you print the results."

    # no output found 2
    code = "if 4 > 5:\n\tprint('True')"

    assert mathproxyagent.execute_one_python_code(code)[0] == "No output found."

    # return error
    code = "2+'2'"
    assert "Error:" in mathproxyagent.execute_one_python_code(code)[0]

    # save previous status
    mathproxyagent.execute_one_python_code("x=3\ny=x*2")
    assert mathproxyagent.execute_one_python_code("print(y)")[0].strip() == "6"

    code = "print('*'*2001)"
    assert (
        mathproxyagent.execute_one_python_code(code)[0]
        == "Your requested query response is too long. You might have made a mistake. Please revise your reasoning and query."
    )


def test_execute_one_wolfram_query():
    mathproxyagent = MathUserProxyAgent(name="MathChatAgent", human_input_mode="NEVER")
    code = "2x=3"

    try:
        mathproxyagent.execute_one_wolfram_query(code)[0]
    except ValueError:
        print("Wolfrma API key not found. Skip test.")


def test_generate_prompt():
    mathproxyagent = MathUserProxyAgent(name="MathChatAgent", human_input_mode="NEVER")

    assert "customized" in mathproxyagent.generate_init_message(
        problem="2x=4", prompt_type="python", customized_prompt="customized"
    )


if __name__ == "__main__":
    test_add_remove_print()
    test_execute_one_python_code()
    test_generate_prompt()
    test_math_user_proxy_agent()
