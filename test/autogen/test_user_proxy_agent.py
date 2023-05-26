from flaml import oai

KEY_LOC = "test/autogen"


def test_user_proxy_agent():
    try:
        import openai
    except ImportError:
        return
    from flaml.autogen.agent.chat_agent import ChatAgent
    from flaml.autogen.agent.user_proxy_agent import UserProxyAgent

    conversations = {}
    oai.ChatCompletion.start_logging(conversations)
    agent = ChatAgent("chat_agent", config_list=oai.config_list_gpt4_gpt35(key_file_path=KEY_LOC))
    user = UserProxyAgent("human_user", human_input_mode="NEVER", max_consecutive_auto_reply=2)
    agent.receive(
        """Write python code to solve the equation x^3=125. You must write code in the following format. You must always print the result.
        Wait for me to return the result.
        ```python
        # your code
        print(your_result)
        ```
        """,
        user,
    )
    print(conversations)


if __name__ == "__main__":
    test_user_proxy_agent()
