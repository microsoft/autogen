from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import json

import autogen
from autogen import oai
from autogen import Agent
from autogen.code_utils import extract_code

from raworkflow.raworkflow_helper import print_messages
from raworkflow import RAWorkflow
from raworkflow.ratwoagentworkflow import TwoAgentWorkflow
from raworkflow.raplannerworkflow import HumanInLoopPlannerExecutor

from utils.code_utils import extract_code_result, learn_skill, utils_2_prompt

import utils.utils
from utils import generate_oai_reply, copy_utils

from enum import Enum


class AgentWorkFlow(Enum):
    CODER_ONLY = "TwoAgents"
    PLANNER_CODER = "PlannerCoder"


# Sorted listed of available RA types
AVAILABLE_RAS = [
    {
        "agent": AgentWorkFlow.CODER_ONLY,
        "title": "Coder Only",
        "description": "A two agent workflow with a coder and an assistant",
    },
    # {
    #     "agent": PLANNER_CODER,
    #     "title": "Planner Coder",
    #     "description": "A two agent workflow with a planner and a coder",
    # },
]


def process_user_message(
    message,
    history,
    utils_dir,
    work_dir,
    ra_type=AgentWorkFlow.CODER_ONLY,
    silent=False,
    agent_on_receive=None,
    path_to_config_list=None,
    personalization_profile=None,
):
    """
    Process the user message and return the response.

    Args:
        message (str): the message from the user
        history (List[Dict]): the list of messages in the chat history
        utils_dir (str): the directory containing the utils files
        work_dir (str): the directory where the code will be executed
        ra_type (str): the type of RA to use
    """

    config_list = autogen.config_list_from_json(path_to_config_list)
    llm_config = {
        # "request_timeout": 600,
        "seed": 42,  # change the seed for different trials
        "config_list": config_list,
        "temperature": 0,
    }

    trigger_memorization = message.strip().lower() == "@memorize"
    if trigger_memorization:
        print("Triggering memorization ...")
        response = learn_skill(history, utils_dir, llm_config)
        return response

    if ra_type == AgentWorkFlow.CODER_ONLY:
        trigger_execution = message.strip().lower() == "@execute"
        ra = TwoAgentWorkflow(
            utils_dir,
            work_dir,
            silent=silent,
            agent_on_receive=agent_on_receive,
            ra_config={
                "trigger_execution": trigger_execution,
                "personalization_profile": personalization_profile,
            },
            llm_config=llm_config,
        )
    elif ra_type == AgentWorkFlow.PLANNER_CODER:
        ra = HumanInLoopPlannerExecutor(
            utils_dir,
            work_dir,
            silent=silent,
            agent_on_receive=agent_on_receive,
            llm_config=llm_config,
        )

    return ra.process_message(
        message,
        history,
    )


def ipython_handle_message(
    message,
    ra_type,
    utils_dir,
    work_dir,
    history,
    path_to_config_list=None,
    silent=False,
):
    """
    Helper function to run IPython in the terminal.
    """
    # Import the required modules
    from IPython.display import Image, display, Markdown

    # Function to display an image
    def display_image(image_path):
        return Image(filename=image_path)

    # Function to display a code file
    def display_code(code_file_path, language="python"):
        with open(code_file_path, "r") as file:
            code_content = file.read()
        formatted_code = f"```{language}\n{code_content}\n```"
        return Markdown(formatted_code)

    response = process_user_message(
        message,
        history=history,
        utils_dir=utils_dir,
        work_dir=work_dir,
        ra_type=ra_type,
        silent=silent,
        path_to_config_list=path_to_config_list,
    )

    # Loop through all images in response/metadata and display them inline
    print(json.dumps(response, indent=2))

    for img_path in response["metadata"]["images"]:
        print(img_path)
        display(display_image(img_path))

    for script_path in response["metadata"]["scripts"]:
        print(script_path)
        display(display_code(script_path))

    for file_path in response["metadata"]["files"]:
        print(file_path)
        display(display_code(file_path))

    history.append(
        {
            "role": "user",
            "content": message,
        }
    )
    response["metadata"]["code"] = response["code"]
    response["metadata"] = json.dumps(response["metadata"])
    history.append(response)
