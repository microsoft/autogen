import os
import autogen  # Assuming you have the autogen module imported or installed
from autogen import oai
from typing import Dict, List, Optional, Tuple, Union


def copy_utils(utils_dir, work_dir):
    # check if utils dir is a single or a list of dirs
    # if it is single dir, convert it to a list
    # TODO: this is a hacky solution, need to find a better way
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    dir_list = utils_dir
    if isinstance(utils_dir, str):
        dir_list = [utils_dir]
    for dirpath in dir_list:
        for file in os.listdir(dirpath):
            if file.endswith(".py"):
                os.system(f"cp {os.path.join(dirpath, file)} {work_dir}")


def create_llm_config(path_to_config_list: str):
    config_list = autogen.config_list_from_json(path_to_config_list)
    llm_config = {
        # "request_timeout": 600,
        "seed": 42,  # Change the seed for different trials
        "config_list": config_list,
        "temperature": 0,
    }
    return llm_config


def generate_oai_reply(
    messages: Optional[List[Dict]] = None,
    llm_config: Optional[Dict] = None,
) -> Tuple[bool, Union[str, Dict, None]]:
    """Generate a reply using autogen.oai."""
    response = oai.ChatCompletion.create(
        messages=messages,
        use_cache=True,
        **llm_config,
    )
    return oai.ChatCompletion.extract_text_or_function_call(response)[0]


def get_standalone_func(content, llm_config):
    messages = [
        {
            "role": "user",
            "content": f"""
        Extract and return a python function from the following text.
        All import statements should be inside the function definitions.
        The function should have a doc string using triple quotes.
        Return the function as plain text without any code blocks.
        The function should not use hardcoded values.
        It should not ask for any user input.
        Instead make them arguments.
        The function should be reusuable for future tasks

        {content}
        """,
        }
    ]
    print("Messages", messages)
    response = generate_oai_reply(messages, llm_config)
    return response
