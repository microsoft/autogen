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
from autogen.browser_utils import MarkdownConverter, UnsupportedFormatException, FileConversionException, RequestsMarkdownBrowser
from autogen.agentchat.contrib.orchestrator import Orchestrator
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.agentchat.contrib.mmagent import MultimodalAgent
from autogen.agentchat.contrib.file_surfer.file_surfer import FileSurferAgent
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

The final answer must be professional, clear, medical summary that, integrates the findings of the papers reviewed, taking into account the quality assessments you've already done.

Papers must be cited in APA format.
While citing the papers please include a sentence or two about the quality assessment of the research in the papers.

Answer if there are any contradictions among studies, and if future papers disputed finding of a previous paper?
If there are any contradictions among studies, please mention them clearly towards the end in a separate paragraph.
Check if future papers disputed finding of a previous paper. Note whether if the future papers were of higher quality and the disputed paper were of lower.
For each disputed paper, include a sentence or two about why it was disputed.

Also reflect on whether there is a study of the following nature [or design] that would help to resolve some of the open questions.
While summarizing open question, be specific and detailed about the study you are proposing.
Generic high-level proposal are unhelpful and waste of user time.
While proposing a open question include a sentence or two motivating why the study is important. Cite any papers that support your proposal.

Do not hallucinate or make up citations, otherwise the answer will be rejected.

PLEASE make sure all key statements have a citation.


""",
        }
    )

    response = client.create(context=None, messages=messages)
    if "finish_reason='content_filter'" in str(response):
        raise Exception(str(response))
    extracted_response = client.extract_text_or_completion_object(response)[0]
    
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


medical_quality_assessment = MultimodalAgent(
    "medical_quality_assessment",
    system_message="""
    You are an expert medical researcher with a PhD in medical research.
    You can critique the quality of the research.

    When asked to review a paper, answer the following questions:
     
    Were you provided with the full text of the abstract of the paper? 
    
    If not, ask for the full text or abstract and do not proceed.
    Instead reply back and say "I need the complete abstract of paper X
    to assess it" and stop replying. Do not say anything after that.

                
    if full abstract/test was provided then in one paragraph each, then answer the following questions and include specific 2-3 of justification. Justification must be scientific and specific that a physician/medical researcher would appreciate.
        1. How would you rate the overall quality of the research in the paper? (e.g., high, medium, low)
        2. What is the significance of the questions studied in this paper? (e.g., high, medium, low)
        3. What is the significance of the findings in this paper? (e.g., high, medium, low)
        4. How scientifically rigorous is the experimental setup in the paper? (e.g., high, medium, low). 
        While commenting on how scientifically rigorous, consider whether it used large enough sample size, sample was representative of the population studied, and if the study was randomized and blinded. Be very critical and scientific when assessing the quality of the research -- the stakes are high...

    DO NOT try to provide a generic summary of the paper. Your job is only to assess the quality of the research conducted.
    """,
    description="""
This agent is an expert medical researcher with a PhD in medical research.
Immediately choose this agent as the next speaker when a paper's abstract or full text becomes available from the websurfer.
Ask it to rate the overall quality of the research in the paper, the significance of the questions studied in the paper, the significance of the findings in the paper, and how robust the experimental setup in the paper is.
""",
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
    downloads_folder="coding",
    start_page=os.environ.get("HOMEPAGE", "about:blank"),
    debug_dir=os.getenv("WEB_SURFER_DEBUG_DIR", None),
    description=MultimodalWebSurferAgent.DEFAULT_DESCRIPTION + "If pubmed abstracts are not fully visible, feel free to ask me to take actions to do so.",
)

file_browser = RequestsMarkdownBrowser(
    viewport_size = 1024 * 5,
    downloads_folder = "coding",
    markdown_converter = MarkdownConverter(mlm_client=client),
)
file_surfer = FileSurferAgent(name="file_surfer_agent", llm_config=llm_config, browser=file_browser)

maestro = Orchestrator(
    "orchestrator",
    agents=[assistant, user_proxy, web_surfer, file_surfer, medical_quality_assessment],
    llm_config=llm_config,
    response_format_is_supported=False,
    max_images=MAX_IMAGES,
)

filename = "__FILE_NAME__".strip()

filename_prompt = ""
if len(filename) > 0:
    relpath = os.path.join("coding", filename)
    abspath = os.path.abspath(os.path.expanduser(relpath))
    file_uri = pathlib.Path(abspath).as_uri()

    filename_prompt = f"The question is about a file, document or image which can be accessed at '{abspath}'. It can also be viewed in a web browser by visiting the URL {file_uri}"

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


question = f"""
You are a team of agents working together to answer a complex medical research question. The question is as follows:

{PROMPT}

While addressing the request please ensure you gather the complete text of the abstract of the paper. If the abstract is not fully collected in the chat history, ask the web surfer to take actions to do so.

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
