from autogen import AssistantAgent, UserProxyAgent, config_list_from_json


async def solve_task(task):
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy",
        code_execution_config={"work_dir": "coding", "use_docker": False},
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", ""),
    )
    await user_proxy.a_initiate_chat(assistant, message=task)

    await user_proxy.a_send(
        f"""Based on the results in above conversation, create a response for the user.
While computing the response, remember that this conversation was your inner mono-logue.
The user does not need to know every detail of the conversation.
All they want to see is the appropriate result for their task (repeated below) in
 a manner that would be most useful. Response should be less than 1500 characters.

 The task was: {task}

There is no need to use the word TERMINATE in this response.

""",
        assistant,
        request_reply=False,
        silent=True,
    )
    response = await assistant.a_generate_reply(assistant.chat_messages[user_proxy], user_proxy)
    await assistant.a_send(response, user_proxy, request_reply=False, silent=True)

    last_message = assistant.chat_messages[user_proxy][-1]["content"]

    return last_message[:2000]
