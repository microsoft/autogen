from autogen import UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.teachable_agent import TeachableAgent


try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


verbosity = 0  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
recall_threshold = 1.5  # Higher numbers allow more (but less relevant) memos to be recalled.
use_cache = False  # If True, cached LLM calls will be skipped and responses pulled from cache. False exposes LLM non-determinism.

# Specify the model to use. GPT-3.5 is less reliable than GPT-4 at learning from user input.
filter_dict = {"model": ["gpt-4"]}


def create_teachable_agent(reset_db=False):
    """Instantiates a TeachableAgent using the settings from the top of this file."""
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict=filter_dict)
    teachable_agent = TeachableAgent(
        name="teachableagent",
        llm_config={"config_list": config_list, "request_timeout": 120, "use_cache": use_cache},
        teach_config={
            "verbosity": verbosity,
            "reset_db": reset_db,
            "path_to_db_dir": "./tmp/interactive/teachable_agent_db",
            "recall_threshold": recall_threshold,
        },
    )
    return teachable_agent


def interact_freely_with_user():
    """Starts a free-form chat between the user and TeachableAgent."""

    # Create the agents.
    print(colored("\nLoading previous memory (if any) from disk.", "light_cyan"))
    teachable_agent = create_teachable_agent(reset_db=False)
    user = UserProxyAgent("user", human_input_mode="ALWAYS")

    # Start the chat.
    teachable_agent.initiate_chat(user, message="Greetings, I'm a teachable user assistant! What's on your mind today?")

    # Let the teachable agent remember things that should be learned from this chat.
    teachable_agent.learn_from_user_feedback()

    # Wrap up.
    teachable_agent.close_db()


if __name__ == "__main__":
    """Lets the user test TeachableAgent interactively."""
    interact_freely_with_user()
