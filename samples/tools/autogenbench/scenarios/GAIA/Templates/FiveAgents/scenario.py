# ruff: noqa: E722
import os
import sys
import json
import autogen
import copy
import traceback
import pathlib
import base64
import re
from datetime import datetime
import testbed_utils
from autogen.token_count_utils import count_token, get_max_token_limit
from autogen.browser_utils import MarkdownConverter, UnsupportedFormatException, FileConversionException
from autogen.agentchat.contrib.orchestrator import Orchestrator
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.agentchat.contrib.mmagent import MultimodalAgent
from autogen.agentchat.contrib.filesurfer import FileSurferAgent
from autogen.code_utils import content_str

MAX_IMAGES = 9
DEFAULT_TEMPERATURE = 0.1

testbed_utils.init()
##############################


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read().strip()

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
)
llm_config = testbed_utils.default_llm_config(config_list, timeout=300)

# Set a low default temperature
for config in llm_config["config_list"]:
    if "temperature" not in config:
        config["temperature"] = DEFAULT_TEMPERATURE
llm_config["temperature"] = DEFAULT_TEMPERATURE
client = autogen.OpenAIWrapper(**llm_config)


def response_preparer(inner_messages):

    messages = [
        {
            "role": "user",
            "content": f"""Earlier you were asked the following:

{PROMPT}

Your team then worked diligently to address that request. Here is a transcript of that conversation:""",
        }
    ]

    # The first message just repeats the question, so remove it
    # if len(inner_messages) > 1:
    #    del inner_messages[0]

    # copy them to this context
    for message in inner_messages:
        if not message.get("content"):
            continue
        message = copy.deepcopy(message)
        message["role"] = "user"
        messages.append(message)

    # ask for the final answer
    messages.append(
        {
            "role": "user",
            "content": f"""
Read the above conversation and output a FINAL ANSWER to the question. The question is repeated here for convenience:

{PROMPT}

To output the final answer, use the following template: FINAL ANSWER: [YOUR FINAL ANSWER]
Your FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
ADDITIONALLY, your FINAL ANSWER MUST adhere to any formatting instructions specified in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)
If you are asked for a number, express it numerically (i.e., with digits rather than words), don't use commas, and don't include units such as $ or percent signs unless specified otherwise.
If you are asked for a string, don't use articles or abbreviations (e.g. for cities), unless specified otherwise. Don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a comma separated list, apply the above rules depending on whether the elements are numbers or strings.
If you are unable to determine the final answer, output 'FINAL ANSWER: Unable to determine'
""",
        }
    )

    response = client.create(context=None, messages=messages)
    if "finish_reason='content_filter'" in str(response):
        raise Exception(str(response))
    extracted_response = client.extract_text_or_completion_object(response)[0]

    # No answer
    if "unable to determine" in extracted_response.lower():
        print("\n>>>Making an educated guess.\n")
        messages.append({"role": "assistant", "content": extracted_response})
        messages.append(
            {
                "role": "user",
                "content": """
I understand that a definitive answer could not be determined. Please make a well-informed EDUCATED GUESS based on the conversation.

To output the educated guess, use the following template: EDUCATED GUESS: [YOUR EDUCATED GUESS]
Your EDUCATED GUESS should be a number OR as few words as possible OR a comma separated list of numbers and/or strings. DO NOT OUTPUT 'I don't know', 'Unable to determine', etc.
ADDITIONALLY, your EDUCATED GUESS MUST adhere to any formatting instructions specified in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)
If you are asked for a number, express it numerically (i.e., with digits rather than words), don't use commas, and don't include units such as $ or percent signs unless specified otherwise.
If you are asked for a string, don't use articles or abbreviations (e.g. for cities), unless specified otherwise. Don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a comma separated list, apply the above rules depending on whether the elements are numbers or strings.
""".strip(),
            }
        )

        response = client.create(context=None, messages=messages)
        if "finish_reason='content_filter'" in str(response):
            raise Exception(str(response))
        extracted_response = client.extract_text_or_completion_object(response)[0]

        return re.sub(r"EDUCATED GUESS:", "FINAL ANSWER:", extracted_response)
    else:
        return extracted_response


assistant = MultimodalAgent(
    "assistant",
    system_message=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
    description=autogen.AssistantAgent.DEFAULT_DESCRIPTION,
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0 or str(x).find("FINAL ANSWER") >= 0,
    code_execution_config=False,
    llm_config=llm_config,
    max_images=MAX_IMAGES,
)

user_proxy_name = "computer_terminal"
user_proxy = autogen.UserProxyAgent(
    user_proxy_name,
    human_input_mode="NEVER",
    description="A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks)",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    default_auto_reply=f'Invalid {user_proxy_name} input: no code block detected.\nPlease provide {user_proxy_name} a complete Python script or a shell (sh) script to run. Scripts should appear in code blocks beginning "```python" or "```sh" respectively.',
    max_consecutive_auto_reply=15,
)

web_surfer = MultimodalWebSurferAgent(
    "web_surfer",
    llm_config=llm_config,
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0 or str(x).find("FINAL ANSWER") >= 0,
    human_input_mode="NEVER",
    headless=True,
    browser_channel="chromium",
    browser_data_dir=None,
    start_page=os.environ.get("HOMEPAGE", "about:blank"),
    debug_dir=os.getenv("WEB_SURFER_DEBUG_DIR", None),
)

file_surfer = FileSurferAgent(name="file_surfer", llm_config=llm_config)

maestro = Orchestrator(
    "orchestrator",
    agents=[assistant, user_proxy, web_surfer, file_surfer],
    llm_config=llm_config,
    response_format_is_supported=False,
    max_images=MAX_IMAGES,
)

filename = "__FILE_NAME__".strip()

filename_prompt = ""
if len(filename) > 0:
    relpath = os.path.join("coding", filename)
    file_uri = pathlib.Path(os.path.abspath(os.path.expanduser(relpath))).as_uri()

    filename_prompt = f"The question is about a file, document or image, which can be accessed by the filename '{filename}' in the current working directory. It can also be viewed in a web browser by visiting the URL {file_uri}"

    mdconverter = MarkdownConverter(mlm_client=client)
    mlm_prompt = f"""Write a detailed caption for this image. Pay special attention to any details that might be useful for someone answering the following:

{PROMPT}
""".strip()

    try:
        res = mdconverter.convert(relpath, mlm_prompt=mlm_prompt)

        if res.text_content:
            if count_token(res.text_content) < 8000:  # Don't put overly-large documents into the prompt
                filename_prompt += "\n\nHere are the file's contents:\n\n" + res.text_content
    except UnsupportedFormatException:
        pass
    except FileConversionException:
        traceback.print_exc()


question = f"""{PROMPT}

{filename_prompt}
""".strip()

try:
    # Initiate one turn of the conversation
    user_proxy.send(
        question,
        maestro,
        request_reply=True,
        silent=False,
    )
except:
    traceback.print_exc()


print()
print(response_preparer(maestro.orchestrated_messages))

##############################
testbed_utils.finalize(agents=[assistant, user_proxy, web_surfer, file_surfer, maestro])
