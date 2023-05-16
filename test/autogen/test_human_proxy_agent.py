from flaml import oai


def test_human_agent():
    try:
        import openai
    except ImportError:
        return
    from flaml.autogen.agent.chat_agent import ChatAgent
    from flaml.autogen.agent.human_proxy_agent import HumanProxyAgent

    conversations = {}
    oai.ChatCompletion.start_logging(conversations)
    agent = ChatAgent("chat_agent")
    user = HumanProxyAgent("human_user", human_input_mode="NEVER", max_consecutive_auto_reply=2)
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
    import openai

    openai.api_key_path = "test/openai/key.txt"
    # if you use Azure OpenAI, comment the above line and uncomment the following lines
    # openai.api_type = "azure"
    # openai.api_base = "https://<your_endpoint>.openai.azure.com/"
    # openai.api_version = "2023-03-15-preview"  # change if necessary
    # openai.api_key = "<your_api_key>"
    # test_extract_code()
    test_human_agent()
