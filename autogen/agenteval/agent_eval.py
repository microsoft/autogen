import os
import sys
from typing import Callable, Dict, List, Optional, Union

from autogen.agenteval.criterion import Criterion
from autogen.agentchat.contrib.agent_eval.critic_agent import CriticAgent
from autogen.agentchat.contrib.agent_eval.quantifier_agent import QuantifierAgent
from autogen.agentchat.contrib.agent_eval.subcritic_agent import SubCriticAgent
from autogen.agenteval.task import Task

import autogen


def generate_criteria(
    llm_config: Optional[Union[Dict, bool]] = None,
    task: Task = None,
    additional_instructions: str = "",
    max_round=2,
    use_subcritic: bool = False,
):
    """
    Creates a list of criteria for evaluating the utility of a given task.
    args:
    - llm_config (dict or bool): llm inference configuration.
    - task (Task): The task to evaluate.
    - additional_instructions (str): Additional instructions for the criteria agent.
    - max_round (int): The maximum number of rounds to run the conversation.
    - use_subcritic (bool): Whether to use the subcritic agent to generate subcriteria.
    returns:
    - list: A list of Criterion objects for evaluating the utility of the given task.
    """
    critic = CriticAgent(
        system_message=CriticAgent.DEFAULT_SYSTEM_MESSAGE + "\n" + additional_instructions,
        llm_config=llm_config,
    )

    critic_user = autogen.UserProxyAgent(
        name="critic_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
    )

    agents = [critic_user, critic]

    if use_subcritic:
        subcritic = SubCriticAgent(
            llm_config=llm_config,
        )
        agents.append(subcritic)

    groupchat = autogen.GroupChat(
        agents=agents, messages=[], max_round=max_round, speaker_selection_method="round_robin"
    )
    critic_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    critic_user.initiate_chat(critic_manager, message=task.sys_msg)
    criteria = critic_user.last_message()
    criteria = Criterion.parse_json_str(criteria["content"])
    return criteria


def quantify_criteria(
    llm_config: Optional[Union[Dict, bool]] = None,
    criteria: List[Criterion] = None,
    task: Task = None,
    test_case: Dict = None,
    ground_truth: str = "",
):
    """
    Quantifies the performance of a system using the provided criteria.
    args:
    - llm_config (dict or bool): llm inference configuration.
    - criteria ([Criterion]): A list of criteria for evaluating the utility of a given task.
    - task (Task): The task to evaluate.
    - test_case (dict): The test case to evaluate.
    - ground_truth (str): The ground truth for the test case.
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
        + str(test_case),
    )
    quantified_results = quantifier_user.last_message()
    return {"actual_success": ground_truth, "estimated_performance": quantified_results["content"]}
