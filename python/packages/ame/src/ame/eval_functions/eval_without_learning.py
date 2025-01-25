from typing import Dict

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.agentic_memory import Apprentice, Grader, PageLogger
from ..eval import Evaluator


async def eval_without_learning(apprentice: Apprentice, evaluator: Evaluator, client: ChatCompletionClient,
                                logger: PageLogger, settings: Dict, run_dict: Dict) -> str:
    """
    Performs an evaluation without the benefit of memory.
    """
    logger.enter_function()

    num_trials = settings["num_trials"]

    # Get the task and advice strings.
    task_file = run_dict["task_file"]
    task_description, expected_answer = evaluator.get_task_description_and_answer_from_file(task_file)

    # Clear memory then run a baseline test.
    logger.info("To get a baseline, clear memory, then assign the task.")
    apprentice.reset_memory()
    num_successes, num_trials = await evaluator.test_apprentice(
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
