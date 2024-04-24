import os
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.agentchat.contrib.mmagent import MultimodalAgent

from config_manager import ConfigManager

config = ConfigManager()
config.initialize()


web_surfer = MultimodalWebSurferAgent(
    "web_surfer",
    llm_config=config.llm_config,
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0 or str(x).find("FINAL ANSWER") >= 0,
    human_input_mode="NEVER",
    headless=True,
    browser_channel="chromium",
    browser_data_dir=None,
    start_page="https://bing.com",
    debug_dir=os.path.join(os.path.dirname(__file__), "debug"),
)

user_proxy = MultimodalAgent(
    "user_proxy",
    system_message="""You are a general-purpose AI assistant and can handle many questions -- but you don't have access to a web browser. However, the user you are talking to does have a browser, and you can see the screen. Provide short direct instructions to them to take you where you need to go to answer the initial question posed to you.

Once the user has taken the final necessary action to complete the task, and you have fully addressed the initial request, reply with the word TERMINATE.""",
    llm_config=config.llm_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda x: False,
    max_consecutive_auto_reply=20,
)

task = input("Enter the task: ")

web_surfer.initiate_chat(
    user_proxy,
    message=task,
    clear_history=True,
)
