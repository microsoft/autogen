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
    config_list = oai.config_list_openai_aoai(KEY_LOC, exclude="aoai")
    functions = [
        {
            "name": "eval_math_responses",
            "description": "Select a response for a math problem using voting, and check if the response is correct if the solution is provided",
            "parameters": {
                "type": "object",
                "properties": {
                    "responses": {
                        "type": "string",
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
        model="gpt-3.5-turbo-0613",
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
    if isinstance(arguments["responses"], str):
        arguments["responses"] = json.loads(arguments["responses"])
    arguments["responses"] = [f"\\boxed{{{x}}}" for x in arguments["responses"]]
    print(arguments["responses"])
    arguments["solution"] = f"\\boxed{{{arguments['solution']}}}"
    print(eval_math_responses(**arguments))


if __name__ == "__main__":
    test_eval_math_responses()
