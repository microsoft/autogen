import os
import json
import testbed_utils
import autogen
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from mmagent import MultimodalAgent

testbed_utils.init()
##############################

# Read the prompt
TASK = None
with open("task_prompt.json.txt", "rt") as fh:
    TASK = json.loads(fh.read())

config_list = autogen.config_list_from_json("OAI_CONFIG_LIST")
llm_config = testbed_utils.default_llm_config(config_list, timeout=300)

# Figure out the starting URL
start_url = {
    "__SHOPPING__": os.getenv("SHOPPING_URL"),
    "__SHOPPING_ADMIN__": os.getenv("SHOPPING_ADMIN_URL"),
    "__REDDIT__": os.getenv("REDDIT_URL"),
    "__GITLAB__": os.getenv("GITLAB_URL"),
    "__MAP__": os.getenv("MAP_URL"),
    "__WIKIPEDIA__": os.getenv("WIKIPEDIA_URL"),
    "__HOMEPAGE__": os.getenv("HOMEPAGE_URL"),
}

# Figure out the user name
user_name = {
    "__REDDIT__": os.getenv("REDDIT_USER_NAME"),
}

# Figure out the password
password = {
    "__REDDIT__": os.getenv("REDDIT_PASSWORD"),
}

web_surfer = MultimodalWebSurferAgent(
    "web_surfer",
    llm_config=llm_config,
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    human_input_mode="NEVER",
    headless=True,
    chromium_channel="chromium",
    chromium_data_dir=None,
    start_page=os.getenv("HOMEPAGE_URL"),
    debug_dir=os.getenv("WEB_SURFER_DEBUG_DIR", None),
)

user_proxy = MultimodalAgent(
    "user_proxy",
    system_message="""You are a general-purpose AI assistant and can handle many questions -- but you don't have access to a web browser. However, the user you are talking to does have a browser, and you can see the screen. Provide short direct instructions to them to take you where you need to go to answer the initial question posed to you.

Once the user has taken the final necessary action to complete the task, and you have fully addressed the initial request, reply with the word TERMINATE.""",
    llm_config=llm_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0,
    max_consecutive_auto_reply=20,
)


user_proxy.initiate_chat(
    web_surfer,
    message=f"Navigate to {start_url[TASK['start_url']]}. Click \"Log in\", type the username '{user_name[TASK['start_url']]}', and password is '{password[TASK['start_url']]}'. Finally click the login button.",
    clear_history=True,
)

user_proxy.reset()
web_surfer.reset()

user_proxy.send(f"Navigate to {start_url[TASK['start_url']]}", web_surfer, request_reply=True)

user_proxy.reset()
web_surfer.reset()

web_surfer.initiate_chat(
    user_proxy,
    message=f"""
We are visiting the website {start_url[TASK['start_url']]}, which is a Postmill forum populated with a large sample of data crawled from Reddit. Postmill is similar to Reddit, but the UI is distinct, and 'subreddits' begin with /f/ rather than /r/. On this website, please complete the following task:

{TASK['intent']}
""".strip(),
    clear_history=True,
)

##############################
testbed_utils.finalize(agents=[web_surfer, user_proxy])
