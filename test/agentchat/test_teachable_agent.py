import sys
from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.teachable_agent import TeachableAgent


def in_color(text, color):
    # Available colors:
    # 90 = grey
    # 91 = red
    # 92 = green
    # 93 = yellow
    # 94 = blue
    # 95 = magenta
    # 96 = cyan
    # 97 = white
    return "\033[{}m".format(color) + text + "\033[0m"


def interact_freely_with_user():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4-0613"]})

    # Create the agents.
    assistant = TeachableAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent("user_proxy", human_input_mode="ALWAYS")

    # Start the chat.
    print(in_color("\nTo clear the context and start a new chat, type 'new chat'.", 93))
    user_proxy.initiate_chat(assistant, message="Hi")


def test_question_answer_pair():
    print(in_color("\n<START TEST OF QUESTION-ANSWER PAIR>", 92))

    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4-0613"]})

    # Create the agents.
    agent = TeachableAgent("agent", llm_config={"config_list": config_list})
    user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    # Ask the agent to do something using terminology it doesn't understand.
    user.initiate_chat(recipient=agent, message="What is the twist of 5 and 7?")

    # Explain the terminology to the agent.
    user.send(recipient=agent, message="The twist of two or more numbers is their product minus their sum.")
    agent_response = user.last_message(agent)
    assert '23' in agent_response["content"]  # GPT-4 usually gets the right answer here, which is 23.

    # Let the agent remember things that should be learned from this chat.
    agent.learn_from_recent_user_comments()

    # Now start a new chat to clear the context, and require the agent to use its new knowledge.
    print(in_color("<STARTING A NEW CHAT WITH EMPTY CONTEXT>", 92))
    user.initiate_chat(recipient=agent, message="What's the twist of 8 and 3 and 2?")
    agent_response = user.last_message(agent)
    assert '35' in agent_response["content"]  # GPT-4 usually gets the right answer here, which is 35.

    # End of test
    agent.delete_db()
    print(in_color("<TEST COMPLETED>", 92))


def test_task_advice_pair():
    print(in_color("\n<START TEST OF TASK-ADVICE PAIR>", 92))

    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4-0613"]})

    # Create the agents.
    agent = TeachableAgent("agent", llm_config={"config_list": config_list})
    user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    # Ask the agent to do something, and provide some helpful advice.
    user.initiate_chat(recipient=agent, message="Compute the twist of 5 and 7. Here's a hint: The twist of two or more numbers is their product minus their sum.")
    agent_response = user.last_message(agent)
    assert '23' in agent_response["content"]  # GPT-4 usually gets the right answer here, which is 23.

    # Let the agent remember things that should be learned from this chat.
    agent.learn_from_recent_user_comments()

    # Now start a new chat to clear the context, and require the agent to use its new knowledge.
    print(in_color("<STARTING A NEW CHAT WITH EMPTY CONTEXT>", 92))
    user.initiate_chat(recipient=agent, message="What's the twist of 8 and 3 and 2?")
    agent_response = user.last_message(agent)
    assert '35' in agent_response["content"]  # GPT-4 usually gets the right answer here, which is 35.

    # End of test
    agent.delete_db()  # Delete the DB now, instead of waiting for garbage collection to do it.
    print(in_color("<TEST COMPLETED>", 92))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('i'):
            interact_freely_with_user()
            exit()

    test_question_answer_pair()
    test_task_advice_pair()
    print(in_color("\n<TEACHABLE AGENT TESTS COMPLETED SUCCESSFULLY>", 92))
