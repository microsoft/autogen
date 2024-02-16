# ruff: noqa: E722
import os
import sys
import json
import autogen
import copy
import traceback
import mimetypes
import base64
import re
from datetime import datetime
import testbed_utils
from autogen.agentchat.contrib.web_surfer import WebSurferAgent
from autogen.token_count_utils import count_token, get_max_token_limit
from autogen.agentchat.contrib.functions import file_utils as futils
from orchestrator import Orchestrator

testbed_utils.init()
##############################

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Read the prompt
PROMPT = ""
with open("prompt.txt", "rt") as fh:
    PROMPT = fh.read().strip()

config_list = autogen.config_list_from_json( "OAI_CONFIG_LIST",)
llm_config = testbed_utils.default_llm_config(config_list, timeout=300)
llm_config["temperature"] = 0.1

summarizer_llm_config = llm_config
final_llm_config = llm_config

client = autogen.OpenAIWrapper(**final_llm_config)
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
YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
If you are asked for a number, don’t use comma to write your number neither use units such as $ or percent sign unless specified otherwise, and don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a string, don’t use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string. 
If you are unable to determine the final answer, output 'FINAL ANSWER: Unable to determine.'
""",
        }
    )

    response = client.create(context=None, messages=messages)
    extracted_response = client.extract_text_or_completion_object(response)[0]

    # No answer
    if "unable to determine" in extracted_response.lower():
        print("\n>>>Making an educated guess.\n")
        messages.append({"role": "assistant", "content": extracted_response })
        messages.append({"role": "user", "content": """
I understand that a definitive answer could not be determined. Please make a well-informed EDUCATED GUESS based on the conversation.

To output the educated guess, use the following template: EDUCATED GUESS: [YOUR EDUCATED GUESS]
YOUR EDUCATED GUESS should be a number OR as few words as possible OR a comma separated list of numbers and/or strings. DO NOT OUTPUT 'I don't know', 'Unable to determine', etc.
If you are asked for a number, don’t use comma to write your number neither use units such as $ or percent sign unless specified otherwise, and don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a string, don’t use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.
If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string. 
""".strip()})

        response = client.create(context=None, messages=messages)
        extracted_response = client.extract_text_or_completion_object(response)[0]
        return re.sub(r"EDUCATED GUESS:", "FINAL ANSWER:", extracted_response)  
    else:
        return extracted_response

assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
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

maestro = Orchestrator(
    "orchestrator",
    agents=[assistant, user_proxy, web_surfer],
    llm_config=llm_config,
)

filename = "__FILE_NAME__".strip()

filename_prompt = ""
if len(filename) > 0:
    content_type, encoding = mimetypes.guess_type(filename)
    relpath = os.path.join("coding", filename)
    filename_prompt = f"The question is about a file, document or image, which can be read from the file '{filename}' in current working directory."
    if re.search(r"\.docx?$", filename.lower()):
        filename_prompt += " It is a word document. Its contents are:\n\n" + futils.read_text_from_docx(relpath)
    elif re.search(r"\.xlsx?$", filename.lower()):
        filename_prompt += " It is an excel document. Its contents are:\n\n" + futils.read_text_from_xlsx(relpath)
    elif re.search(r"\.pptx?$", filename.lower()):
        filename_prompt += " It is an powerpoint document. Its contents are:\n\n" + futils.read_text_from_pptx(relpath)
    elif re.search(r"\.pdf$", filename.lower()):
        filename_prompt += " It is a PDF. Its contents are:\n\n" + futils.read_text_from_pdf(relpath)
    elif re.search(r"\.mp3$", filename.lower()):
        from pydub import AudioSegment

        sound = AudioSegment.from_mp3(relpath)
        wave_fname = relpath + ".wav"
        sound.export(wave_fname, format="wav")
        filename_prompt += " It is an Audio file. Here is its transcript:\n\n" + futils.read_text_from_audio(wave_fname)
    elif re.search(r"\.wav$", filename.lower()):
        filename_prompt += " It is an Audio file. Here is its transcript:\n\n" + futils.read_text_from_audio(relpath)
    elif re.search(r"\.jpe?g$", filename.lower()):
        filename_prompt += " It is an image with the following description:\n\n "

        img_prompt = f"""
Provide a meaningful but concise alt-text description of the image following established best practices (which focus on conveying context, meaning, information and purpose in addition to "looks"). This text should be useful for a low-vision or blind user encountering the image in the context of addressing the following request:

{PROMPT}
        """.strip()
        filename_prompt += futils.caption_image_using_gpt4v( "data:image/jpeg;base64," + encode_image(relpath), img_prompt)
        ocr = futils.read_text_from_image(relpath).strip()
        if ocr != "":
            filename_prompt += "\n\nAdditionally, OCR analysis has detected the following text in the image: \"" + ocr + "\""
    elif re.search(r"\.png$", filename.lower()):
        filename_prompt += " It is an image with the following description:\n\n "

        img_prompt = f"""
Provide a meaningful but concise alt-text description of the image following established best practices (which focus on conveying context, meaning, information and purpose in addition to "looks"). This text should be useful for a low-vision or blind user encountering the image in the context of addressing the following request:

{PROMPT}
        """.strip()
        filename_prompt += futils.caption_image_using_gpt4v( "data:image/png;base64," + encode_image(relpath), img_prompt)

        from PIL import Image

        img = Image.open(relpath)
        # Remove transparency
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        jpg_name = relpath + ".jpg"
        img.save(jpg_name)

        ocr = futils.read_text_from_image(jpg_name).strip()
        if ocr != "":
            filename_prompt += "\n\nAdditionally, OCR analysis has detected the following text in the image: \"" + ocr + "\""
    elif content_type is not None and "text/" in content_type.lower():
        with open(relpath, "rt") as fh:
            filename_prompt += "Here are the file's contents:\n\n" + fh.read().strip()

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
