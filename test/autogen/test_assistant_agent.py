import os
import sys
import pytest
from flaml import oai
from flaml.autogen.agent import AssistantAgent, UserProxyAgent

KEY_LOC = "test/autogen"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"
here = os.path.abspath(os.path.dirname(__file__))


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows",
)
def test_ai_user_proxy_agent():
    try:
        import openai
    except ImportError:
        return

    conversations = {}
    oai.ChatCompletion.start_logging(conversations)

    config_list = oai.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
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

    ai_user_proxy = UserProxyAgent(
        name="ai_user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        code_execution_config=False,
        oai_config={
            "config_list": config_list,
        },
        # In the system message the "user" always refers to ther other agent.
        system_message="You ask a user for help. You check the answer from the user and provide feedback.",
    )
    assistant.reset()

    math_problem = "$x^3=125$. What is x?"
    ai_user_proxy.initiate_chat(
        assistant,
        message=math_problem,
    )
    print(conversations)


def test_gpt35(human_input_mode="NEVER", max_consecutive_auto_reply=5):
    try:
        import openai
    except ImportError:
        return
    config_list = oai.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": {
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-0301",
                "chatgpt-35-turbo-0301",
                "gpt-35-turbo-v0301",
            },
        },
    )
    assistant = AssistantAgent(
        "coding_agent",
        oai_config={
            # "request_timeout": 600,
            "seed": 42,
            "config_list": config_list,
            "max_tokens": 1024,
        },
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
    )
    user.initiate_chat(assistant, message="TERMINATE")
    # should terminate without sending any message
    assert assistant.oai_conversations[user.name][-1]["content"] == "TERMINATE"
    assistant.reset()
    coding_task = "Print hello world to a file called hello.txt"
    user.initiate_chat(assistant, message=coding_task)
    # coding_task = "Create a powerpoint with the text hello world in it."
    # assistant.receive(coding_task, user)
    assistant.reset()
    coding_task = "Save a pandas df with 3 rows and 3 columns to disk."
    user.initiate_chat(assistant, message=coding_task)
    assert not isinstance(user.use_docker, bool)  # None or str


def test_create_execute_script(human_input_mode="NEVER", max_consecutive_auto_reply=10):
    try:
        import openai
    except ImportError:
        return

    config_list = oai.config_list_from_json(OAI_CONFIG_LIST, file_location=KEY_LOC)
    conversations = {}
    oai.ChatCompletion.start_logging(conversations)
    assistant = AssistantAgent(
        "assistant",
        oai_config={
            "request_timeout": 600,
            "seed": 42,
            "config_list": config_list,
        },
    )
    user = UserProxyAgent(
        "user",
        human_input_mode=human_input_mode,
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    )
    user.initiate_chat(
        assistant,
        message="""Create and execute a script to plot a rocket without using matplotlib""",
    )
    assistant.reset()
    user.initiate_chat(
        assistant,
        message="""Create a temp.py file with the following content:
```
print('Hello world!')
```""",
    )
    print(conversations)
    oai.ChatCompletion.start_logging(compact=False)
    user.send("""Execute temp.py""", assistant)
    print(oai.ChatCompletion.logged_history)
    oai.ChatCompletion.stop_logging()


def test_tsp(human_input_mode="NEVER", max_consecutive_auto_reply=10):
    try:
        import openai
    except ImportError:
        return

    config_list = oai.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": ["gpt-4", "gpt4", "gpt-4-32k", "gpt-4-32k-0314"],
        },
    )
    hard_questions = [
        "What if we must go from node 1 to node 2?",
        "Can we double all distances?",
        "Can we add a new point to the graph? It's distance should be randomly between 0 - 5 to each of the existing points.",
    ]

    class TSPUserProxyAgent(UserProxyAgent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            with open(f"{here}/tsp_prompt.txt", "r") as f:
                self._prompt = f.read()

        def generate_init_message(self, question) -> str:
            return self._prompt.format(question=question)

    oai.ChatCompletion.start_logging()
    assistant = AssistantAgent("assistant", oai_config={"temperature": 0, "config_list": config_list})
    user = TSPUserProxyAgent(
        "user",
        code_execution_config={"work_dir": here},
        human_input_mode=human_input_mode,
        max_consecutive_auto_reply=max_consecutive_auto_reply,
    )
    # agent.receive(prompt.format(question=hard_questions[0]), user)
    # agent.receive(prompt.format(question=hard_questions[1]), user)
    user.initiate_chat(assistant, question=hard_questions[2])
    print(oai.ChatCompletion.logged_history)
    oai.ChatCompletion.stop_logging()


if __name__ == "__main__":
    test_gpt35()
    # test_create_execute_script(human_input_mode="TERMINATE")
    # when GPT-4, i.e., the DEFAULT_MODEL, is used, conversation in the following test
    # should terminate in 2-3 rounds of interactions (because is_termination_msg should be true after 2-3 rounds)
    # although the max_consecutive_auto_reply is set to 10.
    # test_tsp(human_input_mode="NEVER", max_consecutive_auto_reply=10)
