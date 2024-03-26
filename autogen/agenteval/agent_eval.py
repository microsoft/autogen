from criterion import Criterion
from test_case import TestCase
from critic_agent import CriticAgent
from quantifier_agent import QuantifierAgent
import autogen

import os
import sys
from typing import Callable, Dict, Optional, Union

sys.path.insert(0, os.path.abspath(os.path.join("..", "agentchat", "contrib")))


def generate_criteria(llm_config: Optional[Union[Dict, bool]] = None, task=None):
    critic = CriticAgent(
        llm_config=llm_config,
    )

    critic_user = autogen.UserProxyAgent(
        name="critic_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={
            "use_docker": False
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    "_".join(task.name.split()).lower()
    critic_user.initiate_chat(critic, message=task.sys_msg)
    criteria = critic_user.last_message()
    criteria = Criterion.parse_json_str(criteria["content"])
    return criteria


def quantify_criteria(llm_config: Optional[Union[Dict, bool]] = None, criteria=None, task=None, test_case=None):
    quantifier = QuantifierAgent(
        llm_config=llm_config,
    )

    quantifier_user = autogen.UserProxyAgent(
        name="quantifier_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={
            "use_docker": False
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    cq_results = quantifier_user.initiate_chat(  # noqa: F841
        quantifier,
        message=task.sys_msg
        + "Evaluation dictionary: "
        + Criterion.write_json(criteria)
        + "actual test case to evaluate: "
        + test_case.output_dictionary,
    )
    quantified_results = quantifier_user.last_message()
    return {"actual_success": test_case.correctness, "estimated_performance": quantified_results["content"]}
