import asyncio
import sys
from typing import Any, Dict, Literal

import pytest
from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.experimental.task_centric_memory.utils import (
    Apprentice,
    ChatCompletionClientRecorder,
    Grader,
    PageLogger,
)
from autogen_ext.models.replay import ReplayChatCompletionClient
from utils import create_oai_client, load_yaml_file

"""
This code sample connects task-centric memory to a selectable agent with no changes to that agent's code.
See the block diagram in the README for an overview of the components and their interactions.
See the config file configs/self_teaching.yaml for an overall view of the structure and settings in this sample.

Execute the sample with this command:
    python eval_self_teaching.py configs/self_teaching.yaml

We say that an agent is self-teaching if it can learn quickly from its own trial and error with no user input.
This sample asks the agent to perform a reasoning task on which it usually fails.
Then using automatic success or failure feedback (for a verifiable task with no side-effects on the environment),
the agent iterates through a background learning loop to find a solution, which it then stores as an insight in memory.
Finally the agent is tested again to see if it can retrieve and apply its insight to the original task,
as well as to a similar but different task as a test of generalization.

If adapting this sample code to a new setting, the Apprentice class can be used or completely replaced by other code.
"""


async def eval_self_teaching(
    apprentice: Apprentice, client: ChatCompletionClient, logger: PageLogger, config: Dict[str, Any]
) -> str:
    """
    Evaluates the ability of an agent to learn quickly from its own trial and error.
    """
    logger.enter_function()

    num_loops = config["num_loops"]
    num_final_test_trials = config["num_final_test_trials"]
    grader = Grader(client, logger)

    # Load the specified data.
    task_dict_1 = load_yaml_file(config["task_file_1"])
    task_description_1 = task_dict_1["task_description"]
    expected_answer_1 = task_dict_1["expected_answer"]

    # Test generalization on this different, similar task.
    task_dict_2 = load_yaml_file(config["task_file_2"])
    task_description_2 = task_dict_2["task_description"]
    expected_answer_2 = task_dict_2["expected_answer"]

    # Start the test with empty memory.
    apprentice.reset_memory()

    total_num_successes_1 = 0
    total_num_successes_2 = 0
    total_num_trials = 0
    for _ in range(num_loops):
        # Train on the first task.
        await apprentice.train_on_task(task=task_description_1, expected_answer=expected_answer_1)

        # Test on the first task.
        num_successes, num_trials = await grader.test_apprentice(
            apprentice=apprentice,
            task_description=task_description_1,
            expected_answer=expected_answer_1,
            num_trials=num_final_test_trials,
            use_memory=True,
            client=client,
        )
        logger.info("Task 1 success rate:  {}%".format(round((num_successes / num_trials) * 100)))
        total_num_successes_1 += num_successes

        # Test on the second task.
        num_successes, num_trials = await grader.test_apprentice(
            apprentice=apprentice,
            task_description=task_description_2,
            expected_answer=expected_answer_2,
            num_trials=num_final_test_trials,
            use_memory=True,
            client=client,
        )
        logger.info("Task 2 success rate:  {}%".format(round((num_successes / num_trials) * 100)))
        total_num_successes_2 += num_successes

        total_num_trials += num_final_test_trials
        logger.info("")

    overall_success_rate_1 = round((total_num_successes_1 / total_num_trials) * 100)
    overall_success_rate_2 = round((total_num_successes_2 / total_num_trials) * 100)

    results_str_1 = "Overall task 1 success rate:  {}%".format(overall_success_rate_1)
    results_str_2 = "Overall task 2 success rate:  {}%".format(overall_success_rate_2)
    logger.info("\n" + results_str_1)
    logger.info(results_str_2)

    logger.leave_function()
    return "\neval_self_teaching\n" + results_str_1 + "\n" + results_str_2


@pytest.mark.asyncio
async def test_memory(mode: Literal["record", "replay"] = "replay") -> None:
    """
    Tests memory using the components specified in the config file.
    By default, mode is "replay", which uses a pre-recorded session file.
    If mode is "record", a new session file is generated for future replay.
    """
    test = "self_teaching"
    config = load_yaml_file(f"./tests/task_centric_memory/configs/{test}.yaml")

    # Create the necessary components.
    logger = PageLogger(config["PageLogger"])
    if mode == "record":
        # To record a session, we need a real client.
        base_client = create_oai_client(config["client"])
    else:
        # To replay a session (as in pytest), we can use a mock client.
        base_client = ReplayChatCompletionClient(
            [
                "not used",
            ]
        )
    client = ChatCompletionClientRecorder(
        base_client, mode, f"./tests/task_centric_memory/sessions/{test}/session.json", logger
    )
    apprentice = Apprentice(client, config["Apprentice"], logger)

    # Call the example function.
    await eval_self_teaching(apprentice, client, logger, config["test"])

    # Clean up.
    client.finalize()


if __name__ == "__main__":
    args = sys.argv[1:]
    # Replay mode is enabled by default.
    # Record mode is enabled if the first argument is "record".
    #   Use this to generate a new session file for pytest to use.
    mode: Literal["record", "replay"] = "replay"
    if (len(args) >= 1) and (args[0] == "record"):
        mode = "record"
    asyncio.run(test_memory(mode=mode))
