from flaml.autogen.code_utils import extract_code
from flaml import oai


def test_extract_code():
    print(extract_code("```bash\npython temp.py\n```"))


def test_coding_agent(human_input_mode="NEVER", max_consecutive_auto_reply=10):
    try:
        import openai
    except ImportError:
        return
    from flaml.autogen.agent.coding_agent import PythonAgent
    from flaml.autogen.agent.human_proxy_agent import HumanProxyAgent

    conversations = {}
    oai.ChatCompletion.start_logging(conversations)
    agent = PythonAgent("coding_agent", request_timeout=600, seed=42)
    user = HumanProxyAgent(
        "user",
        human_input_mode=human_input_mode,
        max_consecutive_auto_reply=max_consecutive_auto_reply,
        is_termination_msg=lambda x: x.rstrip().endswith("TERMINATE"),
    )
    agent.receive(
        """Create and execute a script to plot a rocket without using matplotlib""",
        user,
    )
    agent.reset()
    agent.receive(
        """Create a temp.py file with the following content:
```
print('Hello world!')
```""",
        user,
    )
    print(conversations)
    oai.ChatCompletion.start_logging(compact=False)
    agent.receive("""Execute temp.py""", user)
    print(oai.ChatCompletion.logged_history)
    oai.ChatCompletion.stop_logging()


def test_tsp(human_input_mode="NEVER", max_consecutive_auto_reply=10):
    try:
        import openai
    except ImportError:
        return
    from flaml.autogen.agent.coding_agent import PythonAgent
    from flaml.autogen.agent.human_proxy_agent import HumanProxyAgent

    hard_questions = [
        "What if we must go from node 1 to node 2?",
        "Can we double all distances?",
        "Can we add a new point to the graph? It's distance should be randomly between 0 - 5 to each of the existing points.",
    ]

    oai.ChatCompletion.start_logging()
    agent = PythonAgent("coding_agent", temperature=0)
    user = HumanProxyAgent(
        "user",
        work_dir="test/autogen",
        human_input_mode=human_input_mode,
        max_consecutive_auto_reply=max_consecutive_auto_reply,
    )
    with open("test/autogen/tsp_prompt.txt", "r") as f:
        prompt = f.read()
    # agent.receive(prompt.format(question=hard_questions[0]), user)
    # agent.receive(prompt.format(question=hard_questions[1]), user)
    agent.receive(prompt.format(question=hard_questions[2]), user)
    print(oai.ChatCompletion.logged_history)
    oai.ChatCompletion.stop_logging()


if __name__ == "__main__":
    import openai

    openai.api_key_path = "test/openai/key.txt"
    # if you use Azure OpenAI, comment the above line and uncomment the following lines
    # openai.api_type = "azure"
    # openai.api_base = "https://<your_endpoint>.openai.azure.com/"
    # openai.api_version = "2023-03-15-preview"  # change if necessary
    # openai.api_key = "<your_api_key>"
    # test_extract_code()
    test_coding_agent(human_input_mode="TERMINATE")
    # when GPT-4, i.e., the DEFAULT_MODEL, is used, conversation in the following test
    # should terminate in 2-3 rounds of interactions (because is_termination_msg should be true after 2-3 rounds)
    # although the max_consecutive_auto_reply is set to 10.
    test_tsp(human_input_mode="NEVER", max_consecutive_auto_reply=10)
