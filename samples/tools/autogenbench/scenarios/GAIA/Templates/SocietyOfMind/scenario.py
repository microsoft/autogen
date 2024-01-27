# ruff: noqa: E722
import os
import sys
import json
import autogen
import copy
import traceback
from datetime import datetime
import testbed_utils
from autogen.agentchat.contrib.web_surfer import WebSurferAgent
from autogen.agentchat.contrib.society_of_mind_agent import SocietyOfMindAgent
from autogen.agentchat.contrib.group_chat_moderator import GroupChatModerator
from autogen.token_count_utils import count_token, get_max_token_limit

testbed_utils.init()
##############################

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt-4"]},
)
llm_config = testbed_utils.default_llm_config(config_list, timeout=180)
llm_config["temperature"] = 0.1

summarizer_config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt-3.5-turbo-16k"]},
)
summarizer_llm_config = testbed_utils.default_llm_config(summarizer_config_list, timeout=180)
summarizer_llm_config["temperature"] = 0.1

final_config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt-4-1106-preview"]},
)
final_llm_config = testbed_utils.default_llm_config(final_config_list, timeout=180)
final_llm_config["temperature"] = 0.1


client = autogen.OpenAIWrapper(**final_llm_config)


def response_preparer(inner_messages):
    tokens = 0

    messages = [
        {
            "role": "user",
            "content": """Earlier you were asked the following:

__PROMPT__

Your team then worked diligently to address that request. Here is a transcript of that conversation:""",
        }
    ]
    tokens += count_token(messages[-1])

    # The first message just repeats the question, so remove it
    if len(inner_messages) > 1:
        del inner_messages[0]

    # copy them to this context
    for message in inner_messages:
        message = copy.deepcopy(message)
        message["role"] = "user"
        messages.append(message)
        tokens += count_token(messages[-1])

    messages.append(
        {
            "role": "user",
            "content": """
Read the above conversation and output a FINAL ANSWER to the question. The question is repeated here for convenience:

__PROMPT__

To output the final answer, use the following template: FINAL ANSWER: [YOUR FINAL ANSWER]
YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
If you are asked for a number, don’t use comma to write your number neither use units such as $ or percent sign unless specified otherwise, and don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a string, don’t use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string.""",
        }
    )
    tokens += count_token(messages[-1])

    #    # Hardcoded
    #    while tokens > 3200:
    #        mid = int(len(messages) / 2)  # Remove from the middle
    #        tokens -= count_token(messages[mid])
    #        del messages[mid]

    response = client.create(context=None, messages=messages)
    extracted_response = client.extract_text_or_completion_object(response)[0]
    if not isinstance(extracted_response, str):
        return str(extracted_response.model_dump(mode="dict"))  # Not sure what to do here
    else:
        return extracted_response


assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config=llm_config,
)
user_proxy = autogen.UserProxyAgent(
    "computer_terminal",
    human_input_mode="NEVER",
    description="A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks)",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    default_auto_reply="",
    max_consecutive_auto_reply=15,
)

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"

web_surfer = WebSurferAgent(
    "web_surfer",
    llm_config=llm_config,
    summarizer_llm_config=summarizer_llm_config,
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    browser_config={
        "bing_api_key": os.environ["BING_API_KEY"],
        "viewport_size": 1024 * 5,
        "downloads_folder": "coding",
        "request_kwargs": {
            "headers": {"User-Agent": user_agent},
        },
    },
)

filename_prompt = "__FILE_NAME__".strip()
if len(filename_prompt) > 0:
    filename_prompt = f"Consider the file '{filename_prompt}' which can be read from the current working directory. If you need to read or write it, output python code in a code block (```python) to do so. "


question = f"""
Below I will pose a question to you that I would like you to answer. You should begin by listing all the relevant facts necessary to derive an answer, then fill in those facts from memory where possible, including specific names, numbers and statistics. You are Ken Jennings-level with trivia, and Mensa-level with puzzles, so there should be a deep well to draw from. After listing the facts, begin to solve the question in earnest. Here is the question:

{filename_prompt}__PROMPT__
""".strip()

groupchat = GroupChatModerator(
    agents=[user_proxy, assistant, web_surfer],
    first_speaker=assistant,
    max_round=30,
    messages=[],
    speaker_selection_method="auto",
    allow_repeat_speaker=[web_surfer, assistant],
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    send_introductions=True,
    llm_config=llm_config,
)

soc = SocietyOfMindAgent(
    "gaia_agent",
    chat_manager=manager,
    response_preparer=response_preparer,
    llm_config=llm_config,
)

try:
    # Initiate one turn of the conversation
    user_proxy.send(
        question,
        soc,
        request_reply=True,
        silent=False,
    )
except:
    traceback.print_exc()


##############################
testbed_utils.finalize(agents=[soc, assistant, user_proxy, web_surfer, manager])
