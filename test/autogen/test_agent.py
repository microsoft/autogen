def test_agent():
    from flaml.autogen.agent import Agent

    dummy_agent_1 = Agent(name="dummy_agent_1")
    dummy_agent_2 = Agent(name="dummy_agent_2")

    dummy_agent_1.receive("hello", dummy_agent_2)  # receive a str
    dummy_agent_1.receive(
        {
            "content": "hello",
        },
        dummy_agent_2,
    )  # receive a dict

    # receive dict without openai fields to be printed, such as "content", 'function_call'. There should be no error raised.
    pre_len = len(dummy_agent_1.oai_conversations["dummy_agent_2"])
    dummy_agent_1.receive({"message": "hello"}, dummy_agent_2)
    assert pre_len == len(
        dummy_agent_1.oai_conversations["dummy_agent_2"]
    ), "When the message is not an valid openai message, it should not be appended to the oai conversation."

    dummy_agent_1.send("hello", dummy_agent_2)  # send a str
    dummy_agent_1.send(
        {
            "content": "hello",
        },
        dummy_agent_2,
    )  # send a dict

    # receive dict with no openai fields
    pre_len = len(dummy_agent_1.oai_conversations["dummy_agent_2"])
    dummy_agent_1.send({"message": "hello"}, dummy_agent_2)  # send dict with wrong field

    assert pre_len == len(
        dummy_agent_1.oai_conversations["dummy_agent_2"]
    ), "When the message is not a valid openai message, it should not be appended to the oai conversation."


if __name__ == "__main__":
    test_agent()
