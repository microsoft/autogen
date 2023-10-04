import sys
from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.teachable_agent import TeachableAgent


def interact_freely_with_user():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

    # Create the agents.
    assistant = TeachableAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent("user_proxy", human_input_mode="ALWAYS")

    # Start the chat.
    print("\n\033[92mTo clear the context and start a new chat, type 'new chat'\033[0m\n")
    user_proxy.initiate_chat(assistant, message="Hi")


def test_question_answer_pair():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

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
    print('\n\033[92m<STARTING A NEW CHAT WITH EMPTY CONTEXT>\033[0m  ')
    user.initiate_chat(recipient=agent, message="What's the twist of 8 and 3 and 2?")
    agent_response = user.last_message(agent)
    assert '35' in agent_response["content"]  # GPT-4 usually gets the right answer here, which is 35.


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('i'):
            interact_freely_with_user()
            exit()

    test_question_answer_pair()
