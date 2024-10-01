#!/usr/bin/env python3 -m pytest

import json

import pytest
from conftest import reason, skip_openai  # noqa: E402

import autogen
from autogen.agentchat.contrib.agent_eval.agent_eval import generate_criteria, quantify_criteria
from autogen.agentchat.contrib.agent_eval.criterion import Criterion
from autogen.agentchat.contrib.agent_eval.task import Task

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


def remove_ground_truth(test_case: str):
    test_details = json.loads(test_case)
    # need to remove the ground truth from the test details
    correctness = test_details.pop("is_correct", None)
    test_details.pop("correct_ans", None)
    test_details.pop("check_result", None)
    return str(test_details), correctness


if not skip_openai:
    openai_config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        # The Retrieval tool requires at least gpt-3.5-turbo-1106 (newer versions are supported) or gpt-4-turbo-preview models.
        # https://platform.openai.com/docs/models/overview
        filter_dict={
            "api_type": ["openai"],
            "model": [
                "gpt-4o-mini",
                "gpt-3.5-turbo",
            ],
        },
    )

    aoai_config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    success_str = open("test/test_files/agenteval-in-out/samples/sample_math_response_successful.txt", "r").read()
    response_successful = remove_ground_truth(success_str)[0]
    failed_str = open("test/test_files/agenteval-in-out/samples/sample_math_response_failed.txt", "r").read()
    response_failed = remove_ground_truth(failed_str)[0]
    task = Task(
        **{
            "name": "Math problem solving",
            "description": "Given any question, the system needs to solve the problem as consisely and accurately as possible",
            "successful_response": response_successful,
            "failed_response": response_failed,
        }
    )


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_generate_criteria():
    criteria = generate_criteria(task=task, llm_config={"config_list": aoai_config_list})
    assert criteria
    assert len(criteria) > 0
    assert criteria[0].description
    assert criteria[0].name
    assert criteria[0].accepted_values


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_quantify_criteria():
    criteria_file = "test/test_files/agenteval-in-out/samples/sample_math_criteria.json"
    criteria = open(criteria_file, "r").read()
    criteria = Criterion.parse_json_str(criteria)

    test_case = open("test/test_files/agenteval-in-out/samples/sample_test_case.json", "r").read()
    test_case, ground_truth = remove_ground_truth(test_case)

    quantified = quantify_criteria(
        llm_config={"config_list": aoai_config_list},
        criteria=criteria,
        task=task,
        test_case=test_case,
        ground_truth=ground_truth,
    )
    assert quantified
    assert quantified["actual_success"]
    assert quantified["estimated_performance"]
