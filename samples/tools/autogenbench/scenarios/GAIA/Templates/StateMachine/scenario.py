# ruff: noqa: E722
import os
import autogen
import copy
import traceback
import re
import testbed_utils
from autogen.agentchat.contrib.web_surfer import WebSurferAgent
from autogen.token_count_utils import count_token, get_max_token_limit
from autogen.mdconvert import MarkdownConverter, UnsupportedFormatException
from orchestrator import Orchestrator, Quantifier
from reflection_util import ReflectionUtil

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
llm_config["temperature"] = 0.1

gpt4v_azure = {
    "model": "gpt-4-turbo-v",
    "base_url": config_list[0]["base_url"],
    "api_key": config_list[0]["api_key"],
    "max_retries": 65535,
    "api_version": "2023-12-01-preview",
    "max_tokens": 1000,
    "api_type": "azure",
}

summarizer_llm_config = llm_config
final_llm_config = llm_config

client = autogen.OpenAIWrapper(**final_llm_config)
mlm_client = autogen.OpenAIWrapper(**gpt4v_azure)


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
    if len(inner_messages) > 1:
        del inner_messages[0]

    # copy them to this context
    for message in inner_messages:
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
        extracted_response = client.extract_text_or_completion_object(response)[0]
        return re.sub(r"EDUCATED GUESS:", "FINAL ANSWER:", extracted_response)
    else:
        return extracted_response


TracedAssistantAgent = ReflectionUtil.add_tracing_to_class(autogen.AssistantAgent)
assistant = TracedAssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
    llm_config=llm_config,
)
ReflectionUtil.wrap_reply_funcs(assistant)
ReflectionUtil.replace_conversable_agent_properties(assistant)

TracedUserProxyAgent = ReflectionUtil.add_tracing_to_class(autogen.UserProxyAgent)
user_proxy = TracedUserProxyAgent(
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
ReflectionUtil.wrap_reply_funcs(user_proxy)
ReflectionUtil.replace_conversable_agent_properties(user_proxy)

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
TracedWebSurferAgent = ReflectionUtil.add_tracing_to_class(WebSurferAgent)

web_surfer = TracedWebSurferAgent(
    "web_surfer",
    llm_config=llm_config,
    summarizer_llm_config=summarizer_llm_config,
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
    browser_config={
        "bing_api_key": os.environ["BING_API_KEY"],
        "viewport_size": 1024 * 5,
        "downloads_folder": "coding",
        "request_kwargs": {
            "headers": {"User-Agent": user_agent},
        },
    },
)

ReflectionUtil.wrap_reply_funcs(web_surfer)
ReflectionUtil.replace_conversable_agent_properties(web_surfer)

quantifier = Quantifier(
    "quantifier",
    llm_config={"config_list": config_list},
)
ReflectionUtil.wrap_reply_funcs(quantifier)
ReflectionUtil.replace_conversable_agent_properties(quantifier)

TracedOrchestrator = ReflectionUtil.add_tracing_to_class(
    Orchestrator, detailed={"_broadcast_next_step_and_request_reply": ["next_speaker"]}
)
maestro = TracedOrchestrator(
    "orchestrator",
    agents=[assistant, user_proxy, web_surfer],
    llm_config=llm_config,
    quantifier=quantifier,
)

filename = "__FILE_NAME__".strip()

filename_prompt = ""
if len(filename) > 0:
    relpath = os.path.join("coding", filename)
    filename_prompt = f"The question is about a file, document or image, which can be read from the file '{filename}' in current working directory."

    mdconverter = MarkdownConverter(mlm_client=mlm_client)
    mlm_prompt = """Write a detailed caption for this image. Pay special attention to any details that might be useful for someone answering the following:

{PROMPT}
""".strip()

    try:
        res = mdconverter.convert(relpath, mlm_prompt=mlm_prompt)
        filename_prompt += " Here are the file's contents:\n\n" + res.text_content
    except UnsupportedFormatException:
        pass


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
testbed_utils.finalize(agents=[assistant, user_proxy, web_surfer, maestro])
