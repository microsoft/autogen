try:
    import openai
except ImportError:
    openai = None
import pytest
import json
from flaml import oai
from flaml.autogen.math_utils import eval_math_responses

KEY_LOC = "test/autogen"


@pytest.mark.skipif(openai is None, reason="openai not installed")
def test_eval_math_responses():
    config_list = oai.config_list_from_models(
        KEY_LOC, exclude="aoai", model_list=["gpt-4-0613", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k"]
    )
    functions = [
        {
            "name": "eval_math_responses",
            "description": "Select a response for a math problem using voting, and check if the response is correct if the solution is provided",
            "parameters": {
                "type": "object",
                "properties": {
                    "responses": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The responses in a list",
                    },
                    "solution": {
                        "type": "string",
                        "description": "The canonical solution",
                    },
                },
                "required": ["responses"],
            },
        },
    ]
    response = oai.ChatCompletion.create(
        config_list=config_list,
        messages=[
            {
                "role": "user",
                "content": 'evaluate the math responses ["1", "5/2", "5/2"] against the true answer \\frac{5}{2}',
            },
        ],
        functions=functions,
    )
    print(response)
    responses = oai.ChatCompletion.extract_text_or_function_call(response)
    print(responses[0])
    function_call = responses[0]["function_call"]
    name, arguments = function_call["name"], json.loads(function_call["arguments"])
    assert name == "eval_math_responses"
    print(arguments["responses"])
    # if isinstance(arguments["responses"], str):
    #     arguments["responses"] = json.loads(arguments["responses"])
    arguments["responses"] = [f"\\boxed{{{x}}}" for x in arguments["responses"]]
    print(arguments["responses"])
    arguments["solution"] = f"\\boxed{{{arguments['solution']}}}"
    print(eval_math_responses(**arguments))


def test_json_extraction():
    from flaml.autogen.agentchat import UserProxyAgent

    user = UserProxyAgent(name="test", code_execution_config={"use_docker": False})

    jstr = '{\n"location": "Boston, MA"\n}'
    assert user._format_json_str(jstr) == '{"location": "Boston, MA"}'

    jstr = '{\n"code": "python",\n"query": "x=3\nprint(x)"}'
    assert user._format_json_str(jstr) == '{"code": "python","query": "x=3\\nprint(x)"}'

    jstr = '{"code": "a=\\"hello\\""}'
    assert user._format_json_str(jstr) == '{"code": "a=\\"hello\\""}'


def test_execute_function():
    from flaml.autogen.agentchat import UserProxyAgent

    # 1. test calling a simple function
    def add_num(num_to_be_added):
        given_num = 10
        return num_to_be_added + given_num

    user = UserProxyAgent(name="test", function_map={"add_num": add_num})

    # correct execution
    correct_args = {"name": "add_num", "arguments": '{ "num_to_be_added": 5 }'}
    assert user.execute_function(func_call=correct_args)[1]["content"] == "15"

    # function name called is wrong or doesn't exist
    wrong_func_name = {"name": "subtract_num", "arguments": '{ "num_to_be_added": 5 }'}
    assert "Error: Function" in user.execute_function(func_call=wrong_func_name)[1]["content"]

    # arguments passed is not in correct json format
    wrong_json_format = {
        "name": "add_num",
        "arguments": '{ "num_to_be_added": 5, given_num: 10 }',
    }  # should be "given_num" with quotes
    assert "You argument should follow json format." in user.execute_function(func_call=wrong_json_format)[1]["content"]

    # function execution error with wrong arguments passed
    wrong_args = {"name": "add_num", "arguments": '{ "num_to_be_added": 5, "given_num": 10 }'}
    assert "Error: " in user.execute_function(func_call=wrong_args)[1]["content"]

    # 2. test calling a class method
    class AddNum:
        def __init__(self, given_num):
            self.given_num = given_num

        def add(self, num_to_be_added):
            self.given_num = num_to_be_added + self.given_num
            return self.given_num

    user = UserProxyAgent(name="test", function_map={"add_num": AddNum(given_num=10).add})
    func_call = {"name": "add_num", "arguments": '{ "num_to_be_added": 5 }'}
    assert user.execute_function(func_call=func_call)[1]["content"] == "15"
    assert user.execute_function(func_call=func_call)[1]["content"] == "20"


if __name__ == "__main__":
    test_json_extraction()
    test_execute_function()
    test_eval_math_responses()
