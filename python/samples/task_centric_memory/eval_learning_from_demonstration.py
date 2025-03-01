import asyncio
import sys
from typing import Any, Dict

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.experimental.task_centric_memory.utils import Apprentice, Grader, PageLogger
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
    results = await eval_learning_from_demonstration(apprentice, client, logger, config["test"])

    # Finish up.
    print(results)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        # Print usage information.
        print("Usage:  amt.py <path to *.yaml file>")
    else:
        # Run the code example.
        asyncio.run(run_example(config_filepath=args[0]))
