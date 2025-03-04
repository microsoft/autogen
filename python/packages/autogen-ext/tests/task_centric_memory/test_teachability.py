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
See the config file configs/eval_teachability.yaml for an overall view of the structure and settings in this sample.

Execute the sample with this command:
    python eval_teachability.py configs/eval_teachability.yaml

Teachable agents use memory to learn quickly from user teachings, hints, and advice.
The function below passes user instructions (loaded from a file) to the agent by calling Apprentice.handle_user_message().
If adapting this sample code to a new setting, the Apprentice class can be used or completely replaced by other code.

1. In the first conversation, the agent is expected to fail because it lacks the necessary knowledge.
2. In the second conversation (starting with an empty context window), the user provides the missing insight.
3. In the third conversation, the agent is expected to succeed after retrieving the key insight from memory.
"""


async def eval_teachability(
    apprentice: Apprentice, client: ChatCompletionClient, logger: PageLogger, config: Dict[str, Any]
) -> str:
    """
    Evaluates the ability to learn quickly from user teachings, hints, and advice.
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


@pytest.mark.asyncio
async def test_memory(mode: Literal["record", "replay"] = "replay") -> None:
    """
    Tests memory using the components specified in the config file.
    By default, mode is "replay", which uses a pre-recorded session file.
    If mode is "record", a new session file is generated for future replay.
    """
    test = "teachability"
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
    await eval_teachability(apprentice, client, logger, config["test"])

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
