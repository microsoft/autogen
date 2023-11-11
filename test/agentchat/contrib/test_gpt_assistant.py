import pytest
import os
import sys
import autogen

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

try:
    from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

    skip_test = False
except ImportError:
    skip_test = True


def ask_ossinsight(question):
    return f"That is a good question, but I don't know the answer yet. Please ask your human  developer friend to help you. \n\n{question}"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_test,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_gpt_assistant_chat():
    ossinsight_api_schema = {
        "name": "ossinsight_data_api",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Enter your GitHub data question in the form of a clear and specific question to ensure the returned data is accurate and valuable. For optimal results, specify the desired format for the data table in your request.",
                }
            },
            "required": ["question"],
        },
        "description": "This is an API endpoint allowing users (analysts) to input question about GitHub in text format to retrieve the realted and structured data.",
    }

    analyst = GPTAssistantAgent(
        name="Open_Source_Project_Analyst",
        llm_config={"tools": [{"type": "function", "function": ossinsight_api_schema}]},
        instructions="Hello, Open Source Project Analyst. You'll conduct comprehensive evaluations of open source projects or organizations on the GitHub platform",
    )
    analyst.register_function(
        function_map={
            "ossinsight_data_api": ask_ossinsight,
        }
    )

    ok, response = analyst._invoke_assistant(
        [{"role": "user", "content": "What is the most popular open source project on GitHub?"}]
    )
    assert ok is True
    assert response.get("role", "") == "assistant"
    assert len(response.get("content", "")) > 0

    assert analyst.can_execute_function("ossinsight_data_api") is False

    analyst.reset()
    assert len(analyst._openai_threads) == 0


if __name__ == "__main__":
    test_gpt_assistant_chat()
