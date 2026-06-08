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
See the config file configs/demonstration.yaml for an overall view of the structure and settings in this sample.

Execute the sample with this command:
    python eval_learning_from_demonstration.py configs/demonstration.yaml

Here, to learn from a demonstration means to remember a previously demonstrated solution for the same or a similar task.

1. The function below asks the agent to perform a reasoning task (ten times) on which it usually fails.
2. Then agent is then given one demonstration of how to solve a similar but different task, and the context window is cleared.
3. Finally the agent is tested 10 more times to see if it can retrieve and apply the demonstration to the original task.

If adapting this sample code to a new setting, the Apprentice class can be used or completely replaced by other code.
"""


async def eval_learning_from_demonstration(
    apprentice: Apprentice, client: ChatCompletionClient, logger: PageLogger, config: Dict[str, Any]
) -> str:
    """
    Evaluates the ability to learn quickly from demonstrations.
    """
    logger.enter_function()

    num_trials = config["num_trials"]
    grader = Grader(client, logger)

    # Load the specified data.
    main_task = load_yaml_file(config["main_task_file"])
    task_description = main_task["task_description"]
    expected_answer = main_task["expected_answer"]
    demo_task = load_yaml_file(config["demo_task_file"])["task_description"]
    demo_solution = load_yaml_file(config["demo_solution_file"])["insight"]

    # Start by clearing memory then running a baseline test.
    logger.info("To get a baseline, clear memory, then assign the task.")
    apprentice.reset_memory()
    num_successes, num_trials = await grader.test_apprentice(
        apprentice=apprentice,
        task_description=task_description,
        expected_answer=expected_answer,
        num_trials=num_trials,
        use_memory=True,
        client=client,
    )
    success_rate = round((num_successes / num_trials) * 100)
    results_str_1 = "Success rate before demonstration:  {}%".format(success_rate)
    logger.info("\n" + results_str_1)

    # Provide a demonstration for a similar but different task.
    logger.info("Demonstrate a solution to a similar task.")
    await apprentice.add_task_solution_pair_to_memory(demo_task, demo_solution)

    # Now test again to see if the demonstration (retrieved from memory) helps.
    logger.info("Assign the task again to see if the demonstration helps.")
    num_successes, num_trials = await grader.test_apprentice(
        apprentice=apprentice,
        task_description=task_description,
        expected_answer=expected_answer,
        num_trials=num_trials,
        use_memory=True,
        client=client,
    )
    success_rate = round((num_successes / num_trials) * 100)
    results_str_2 = "Success rate after demonstration:  {}%".format(success_rate)
    logger.info("\n" + results_str_2)

    logger.leave_function()
    return "\neval_learning_from_demonstration\n" + results_str_1 + "\n" + results_str_2


@pytest.mark.asyncio
async def test_memory(mode: Literal["record", "replay"] = "replay") -> None:
    """
    Tests memory using the components specified in the config file.
    By default, mode is "replay", which uses a pre-recorded session file.
    If mode is "record", a new session file is generated for future replay.
    """
    test = "demonstration"
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
    await eval_learning_from_demonstration(apprentice, client, logger, config["test"])

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
