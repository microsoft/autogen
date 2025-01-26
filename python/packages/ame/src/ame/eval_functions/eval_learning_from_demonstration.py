from typing import Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.agentic_memory import Apprentice, Grader, PageLogger


async def eval_learning_from_demonstration(apprentice: Apprentice, client: ChatCompletionClient,
                                           logger: PageLogger, settings: Dict, run_dict: Dict) -> str:
    """
    Evaluates the ability to learn quickly from demonstrations.
    """
    logger.enter_function()

    num_trials = settings["num_trials"]
    grader = Grader(client, logger)

    # Load the specified data.
    with open(run_dict["main_task_file"], "r") as file:
        # The task being tested.
        main_task = yaml.load(file, Loader=yaml.FullLoader)
        task_description = main_task["task_description"]
        expected_answer = main_task["expected_answer"]
    with open(run_dict["demo_task_file"], "r") as file:
        # A similar but different task.
        demo_task = yaml.load(file, Loader=yaml.FullLoader)["task_description"]
    with open(run_dict["demo_solution_file"], "r") as file:
        # A demonstration of solving the second task.
        demo_solution = yaml.load(file, Loader=yaml.FullLoader)["demo"]

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
        logger=logger,
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
        logger=logger,
    )
    success_rate = round((num_successes / num_trials) * 100)
    results_str_2 = "Success rate after demonstration:  {}%".format(success_rate)
    logger.info("\n" + results_str_2)

    logger.leave_function()
    return "\neval_learning_from_demonstration\n" + results_str_1 + "\n" + results_str_2
