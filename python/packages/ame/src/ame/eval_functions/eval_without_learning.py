from typing import Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.agentic_memory import Apprentice, Grader, PageLogger


async def eval_without_learning(apprentice: Apprentice, client: ChatCompletionClient,
                                logger: PageLogger, settings: Dict, run_dict: Dict) -> str:
    """
    Performs an evaluation without the benefit of memory.
    """
    logger.enter_function()

    num_trials = settings["num_trials"]
    grader = Grader(client, logger)

    # Load the specified data.
    with open(run_dict["task_file"], "r") as file:
        # The task being tested.
        task = yaml.load(file, Loader=yaml.FullLoader)
        task_description = task["task_description"]
        expected_answer = task["expected_answer"]

    # Clear memory then run a baseline test.
    logger.info("To get a baseline, clear memory, then assign the task.")
    apprentice.reset_memory()
    num_successes, num_trials = await grader.test_apprentice(
        apprentice=apprentice,
        task_description=task_description,
        expected_answer=expected_answer,
        num_trials=num_trials,
        use_memory=True,
        client=client,
        logger=logger,
    )
    success_rate = round((num_successes / num_trials) * 100)
    results_str = "Success rate:  {}%".format(success_rate)
    logger.info("\n" + results_str)

    logger.leave_function()
    return "\neval_without_learning\n" + results_str
