import os
from autogen import UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent


def main():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample.
    # For example, if you have created a OAI_CONFIG_LIST file in the current working directory, that file will be used.
    llm_config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"tags": ["llm"]})
    mlm_config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST", filter_dict={"tags": ["mlm"]})

    web_surfer = MultimodalWebSurferAgent(
        "web_surfer",
        llm_config={"config_list": llm_config_list},
        mlm_config={"config_list": mlm_config_list},
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
        code_execution_config=False,
    )

    # Create the agent that represents the user in the conversation.
    user_proxy = UserProxyAgent("user", code_execution_config=False)

    # Let the assistant start the conversation.  It will end when the user types exit.
    web_surfer.initiate_chat(user_proxy, message="How can I help you today?")


if __name__ == "__main__":
    main()
