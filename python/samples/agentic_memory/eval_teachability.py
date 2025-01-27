import asyncio
import sys
from typing import Dict
import yaml

from autogen_core.models import (
    ChatCompletionClient,
)

from autogen_ext.agentic_memory import Apprentice, Grader, PageLogger

from utils.client import create_oai_client


async def eval_teachability(apprentice: Apprentice, client: ChatCompletionClient, logger: PageLogger, settings: Dict) -> str:
    """
    Evalutes the ability to learn quickly from user teachings, hints, and advice.
    """
    logger.enter_function()

    # Load the specified data.
    with open(settings["task_file"], "r") as file:
        # The task being tested.
        task = yaml.load(file, Loader=yaml.FullLoader)
        task_description = task["task_description"]
        expected_answer = task["expected_answer"]
    with open(settings["advice_file"], "r") as file:
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


async def run_example(settings_filepath) -> None:
    """
    Runs the code example with the necessary components.
    """
    with open(settings_filepath, "r") as file:
        # Create the necessary components.
        settings = yaml.load(file, Loader=yaml.FullLoader)
        logger = PageLogger(settings["PageLogger"])
        client = create_oai_client(settings["client"], logger)
        apprentice = Apprentice(settings["Apprentice"], client, logger)

        # Call the example function.
        results = await eval_teachability(apprentice, client, logger, settings["test"])

        if hasattr(client, "finalize"):
            # If this is a client wrapper, it needs to be finalized.
            client.finalize()

        # Finish up.
        logger.flush(finished=True)
        print(results)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        # Print usage information.
        print("Usage:  amt.py <path to *.yaml file>")
    else:
        # Run the code example.
        asyncio.run(run_example(settings_filepath=args[0]))
