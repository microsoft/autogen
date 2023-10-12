import sys
from autogen import ConversableAgent, UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.teachable_agent import TeachableAgent


try:
    from termcolor import colored
except ImportError:
    def colored(x, *args, **kwargs):
        return x


verbosity = 2
assert_on_error = False

# Load LLM inference endpoints from an env variable or a file
# See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample

# config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4-0613"]})  # OpenAI
# config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-3.5-turbo-0613"]})  # OpenAI

# config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-4"]})  # Azure
config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"model": ["gpt-35-turbo-16k"]})  # Azure


def create_teachable_agent():
    agent = TeachableAgent(
        name="assistant",
        llm_config={"config_list": config_list},
        teach_config={"verbosity": verbosity, "recall_threshold": 1.5})
    return agent


def interact_freely_with_user():
    agent = create_teachable_agent()
    user = UserProxyAgent("user", human_input_mode="ALWAYS")

    # Start the chat.
    print(colored("\nTo clear the context and start a new chat, type 'new chat'.", 'light_cyan'))
    user.initiate_chat(agent, message="Hi")


def check_agent_response(agent, user, correct_answer):
    agent_response = user.last_message(agent)["content"]
    if correct_answer not in agent_response:
        print(colored(f"\nTEST FAILED:  EXPECTED ANSWER {correct_answer} NOT FOUND IN AGENT RESPONSE", 'light_red'))
        if assert_on_error:
            assert correct_answer in agent_response
        return 1
    else:
        print(colored(f"\nTEST PASSED:  EXPECTED ANSWER {correct_answer} FOUND IN AGENT RESPONSE", 'light_cyan'))
        return 0


def test_question_answer_pair():
    print(colored("\nTEST QUESTION-ANSWER PAIRS", 'light_cyan'))
    num_errors = 0
    agent = create_teachable_agent()
    user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    # Ask the agent to do something using terminology it doesn't understand.
    user.initiate_chat(recipient=agent, message="What is the twist of 5 and 7?")

    # Explain the terminology to the agent.
    user.send(recipient=agent, message="The twist of two or more numbers is their product minus their sum.")
    num_errors += check_agent_response(agent, user, "23")

    # Let the agent remember things that should be learned from this chat.
    agent.learn_from_recent_user_comments()

    # Now start a new chat to clear the context, and require the agent to use its new knowledge.
    print(colored("\nSTARTING A NEW CHAT WITH EMPTY CONTEXT", 'light_cyan'))
    user.initiate_chat(recipient=agent, message="What's the twist of 8 and 3 and 2?")
    num_errors += check_agent_response(agent, user, "35")

    # Wrap up.
    agent.delete_db()  # Delete the DB now, instead of waiting for garbage collection to do it.
    return num_errors


def test_task_advice_pair():
    print(colored("\nTEST TASK-ADVICE PAIRS", 'light_cyan'))
    num_errors = 0
    agent = create_teachable_agent()
    user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    # Ask the agent to do something, and provide some helpful advice.
    user.initiate_chat(recipient=agent, message="Compute the twist of 5 and 7. Here's a hint: The twist of two or more numbers is their product minus their sum.")
    num_errors += check_agent_response(agent, user, "23")

    # Let the agent remember things that should be learned from this chat.
    agent.learn_from_recent_user_comments()

    # Now start a new chat to clear the context, and require the agent to use its new knowledge.
    print(colored("\nSTARTING A NEW CHAT WITH EMPTY CONTEXT", 'light_cyan'))
    user.initiate_chat(recipient=agent, message="Please calculate the twist of 8 and 3 and 2.")
    num_errors += check_agent_response(agent, user, "35")

    # Wrap up.
    agent.delete_db()  # Delete the DB now, instead of waiting for garbage collection to do it.
    return num_errors


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('i'):
            interact_freely_with_user()
            exit()

    total_num_errors = 0
    total_num_errors += test_question_answer_pair()
    total_num_errors += test_task_advice_pair()
    if total_num_errors == 0:
        print(colored("\nTEACHABLE AGENT TESTS COMPLETED SUCCESSFULLY", 'light_cyan'))
    else:
        print(colored(f"\nTEACHABLE AGENT TESTS COMPLETED WITH {total_num_errors} TOTAL ERRORS", 'light_red'))
