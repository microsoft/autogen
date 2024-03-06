import os
from autogen import UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.web_surfer import WebSurferAgent


def main():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample.
    # For example, if you have created a OAI_CONFIG_LIST file in the current working directory, that file will be used.
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

    # Create the agent that uses the LLM.
    web_surfer = WebSurferAgent(
        "web_surfer",
        llm_config={"config_list": config_list},
        summarizer_llm_config={"config_list": config_list},
        browser_config={
            "viewport_size": 1024 * 2,
            "downloads_folder": os.getcwd(),
            "bing_api_key": os.environ.get("BING_API_KEY"),
        },
    )

    # Create the agent that represents the user in the conversation.
    user_proxy = UserProxyAgent("user", code_execution_config=False)

    # Let the assistant start the conversation.  It will end when the user types exit.
    web_surfer.initiate_chat(user_proxy, message="How can I help you today?")


if __name__ == "__main__":
    main()
