from typing import Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.agentic_memory import Apprentice, Grader, PageLogger


async def eval_self_teaching(apprentice: Apprentice, client: ChatCompletionClient,
                             logger: PageLogger, settings: Dict, run_dict: Dict) -> str:
    """
    Evaluates the ability of an agent to learn quickly from its own trial and error.
    """
    logger.enter_function()

    num_loops = settings["num_loops"]
    num_final_test_trials = settings["num_final_test_trials"]
    grader = Grader(client, logger)

    # Load the specified data.
    with open(run_dict["task_file_1"], "r") as file:
        # Train and test on this task.
        task_1 = yaml.load(file, Loader=yaml.FullLoader)
        task_description_1 = task_1["task_description"]
        expected_answer_1 = task_1["expected_answer"]
    with open(run_dict["task_file_2"], "r") as file:
        # Test generalization on this different, similar task.
        task_2 = yaml.load(file, Loader=yaml.FullLoader)
        task_description_2 = task_2["task_description"]
        expected_answer_2 = task_2["expected_answer"]

    # Start the test with empty memory.
    apprentice.reset_memory()

    total_num_successes_1 = 0
    total_num_successes_2 = 0
    total_num_trials = 0
    for i in range(num_loops):
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
            logger=logger,
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
            logger=logger,
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
