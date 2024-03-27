import autogen
from criterion import Criterion
from critic_agent import CriticAgent
from quantifier_agent import QuantifierAgent
from task import Task
from test_case import TestCase

import os
import sys
from typing import Callable, Dict, Optional, Union


def generate_criteria(llm_config: Optional[Union[Dict, bool]] = None, task: Task = None):
    """
    Creates a list of criteria for evaluating the utility of a given task.
    args:
    - llm_config (dict or bool): llm inference configuration.
    - task (TestCase): The task to evaluate.
    returns:
    - list: A list of Criterion objects for evaluating the utility of the given task.
    """
    critic = CriticAgent(
        llm_config=llm_config,
    )

    critic_user = autogen.UserProxyAgent(
        name="critic_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
    )

    critic_user.initiate_chat(critic, message=task.sys_msg)
    criteria = critic_user.last_message()
    criteria = Criterion.parse_json_str(criteria["content"])
    return criteria


def quantify_criteria(
    llm_config: Optional[Union[Dict, bool]] = None,
    criteria: [Criterion] = None,
    task: Task = None,
    test_case: TestCase = None,
):
    """
    Quantifies the performance of a system using the provided criteria.
    args:
    - llm_config (dict or bool): llm inference configuration.
    - criteria ([Criterion]): A list of criteria for evaluating the utility of a given task.
    - task (Task): The task to evaluate.
    - test_case (TestCase): The test case to evaluate.
    returns:
    - dict: A dictionary where the keys are the criteria and the values are the assessed performance based on accepted values for each criteria.
    """
    quantifier = QuantifierAgent(
        llm_config=llm_config,
    )

    quantifier_user = autogen.UserProxyAgent(
        name="quantifier_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
    )

    cq_results = quantifier_user.initiate_chat(  # noqa: F841
        quantifier,
        message=task.sys_msg
        + "Evaluation dictionary: "
        + Criterion.write_json(criteria)
        + "actual test case to evaluate: "
        + str(test_case.test_details),
    )
    quantified_results = quantifier_user.last_message()
    return {"actual_success": test_case.correctness, "estimated_performance": quantified_results["content"]}
