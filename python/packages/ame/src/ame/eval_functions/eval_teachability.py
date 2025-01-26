from typing import Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.agentic_memory import Apprentice, Grader, PageLogger


async def eval_teachability(apprentice: Apprentice, client: ChatCompletionClient,
                            logger: PageLogger, settings: Dict, run_dict: Dict) -> str:
    """
    Evalutes the ability to learn quickly from user teachings, hints, and advice.
    """
    logger.enter_function()

    # Load the specified data.
    with open(run_dict["task_file"], "r") as file:
        # The task being tested.
        task = yaml.load(file, Loader=yaml.FullLoader)
        task_description = task["task_description"]
        expected_answer = task["expected_answer"]
    with open(run_dict["advice_file"], "r") as file:
        # Advice for solving such tasks.
        advice = yaml.load(file, Loader=yaml.FullLoader)["advice"]

    # First test without memory.
    apprentice.reset_memory()
    logger.info("\nClear memory, then ask the question.")
    response = await apprentice.handle_user_message(task_description)

    # Check the response.
    grader = Grader(client, logger)
    response_is_correct, extracted_answer = await grader.is_response_correct(
        task_description, response, expected_answer
    )
    logger.info("Extracted answer:  {}".format(extracted_answer))
    if response_is_correct:
        results_str_1 = "Answer before teaching is CORRECT."
    else:
        results_str_1 = "Answer before teaching is INCORRECT."
    logger.info(results_str_1 + "\n")

    # Give advice that should help solve this task.
    logger.info("Give the advice.")
    await apprentice.handle_user_message(advice)

    # Now ask the question again to see if the advice helps.
    logger.info("\nAsk the question again to see if the advice helps.")
    response = await apprentice.handle_user_message(task_description)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(
        task_description, response, expected_answer
    )
    logger.info("Extracted answer:  {}".format(extracted_answer))
    if response_is_correct:
        results_str_2 = "Answer after teaching is CORRECT."
    else:
        results_str_2 = "Answer after teaching is INCORRECT."
    logger.info(results_str_2 + "\n")

    logger.leave_function()
    return "\neval_teachability\n" + results_str_1 + "\n" + results_str_2
