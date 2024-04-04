import os
import json
import testbed_utils
import autogen
import evaluation_harness
import sys
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from mmagent import MultimodalAgent

from evaluation_harness.env_config import ACCOUNTS, GITLAB, MAP, REDDIT, SHOPPING, SHOPPING_ADMIN, WIKIPEDIA, HOMEPAGE

testbed_utils.init()
##############################

# Read the prompt
TASK = None
with open("task_prompt.json.txt", "rt") as fh:
    TASK = json.loads(fh.read())

config_list = autogen.config_list_from_json("OAI_CONFIG_LIST")
llm_config = testbed_utils.default_llm_config(config_list, timeout=300)

web_surfer = MultimodalWebSurferAgent(
    "web_surfer",
    llm_config=llm_config,
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    human_input_mode="NEVER",
    headless=True,
    chromium_channel="chromium",
    chromium_data_dir=None,
    start_page=HOMEPAGE,
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

# BEGIN TODO: Make this conditional on the sites involved
login_url = REDDIT
username = ACCOUNTS["reddit"]["username"]
password = ACCOUNTS["reddit"]["password"]
start_url = TASK["start_url"].replace("__REDDIT__", REDDIT)
if start_url == REDDIT:
    start_url = start_url + "/forums"

user_proxy.initiate_chat(
    web_surfer,
    message=f"Navigate to {login_url}. Click \"Log in\", type the username '{username}', and password is '{password}'. Finally click the login button.",
    clear_history=True,
)
## END TODO

user_proxy.reset()
web_surfer.reset()

user_proxy.send(f"Navigate to {start_url}", web_surfer, request_reply=True)

user_proxy.reset()
web_surfer.reset()

web_surfer.initiate_chat(
    user_proxy,
    message=f"""
We are visiting the website {start_url}, which is a Postmill forum populated with a large sample of data crawled from Reddit. Postmill is similar to Reddit, but the UI is distinct, and 'subreddits' begin with /f/ rather than /r/. On this website, please complete the following task:

{TASK['intent']}
""".strip(),
    clear_history=True,
)

########## EVALUATION ##########

# playwright = web_surfer._playwright
context = web_surfer._context
page = web_surfer._page
cdp_session = context.new_cdp_session(page)
config_file = "full_task.json.txt"
final_answer = "TODO"

evaluator = evaluation_harness.evaluator_router(config_file)
score = evaluator(
    trajectory=evaluation_harness.make_answer_trajecotry(final_answer),
    config_file=config_file,
    page=page,
    client=cdp_session,
)

print("FINAL SCORE: " + str(score))

################################
testbed_utils.finalize(agents=[web_surfer, user_proxy])
