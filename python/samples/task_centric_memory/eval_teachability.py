import asyncio
import sys
from typing import Any, Dict

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.task_centric_memory.utils import Apprentice, Grader, PageLogger

from utils import create_oai_client, load_yaml_file


async def eval_teachability(
    apprentice: Apprentice, client: ChatCompletionClient, logger: PageLogger, config: Dict[str, Any]
) -> str:
    """
    Evalutes the ability to learn quickly from user teachings, hints, and advice.
    """
    logger.enter_function()

    # Load the specified data.
    task_dict = load_yaml_file(config["task_file"])
    task_description = task_dict["task_description"]
    expected_answer = task_dict["expected_answer"]

    insight_dict = load_yaml_file(config["insight_file"])
    insight = insight_dict["insight"]

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
    await apprentice.handle_user_message(insight)

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


async def run_example(config_filepath: str) -> None:
    """
    Runs the code example with the necessary components.
    """
    config = load_yaml_file(config_filepath)

    # Create the necessary components.
    logger = PageLogger(config["PageLogger"])
    client = create_oai_client(config["client"])
    apprentice = Apprentice(client, config["Apprentice"], logger)

    # Call the example function.
    results = await eval_teachability(apprentice, client, logger, config["test"])

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
        asyncio.run(run_example(config_filepath=args[0]))
