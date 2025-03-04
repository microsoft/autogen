import asyncio
import sys
from typing import Any, Dict, Set

from autogen_core.models import (
    ChatCompletionClient,
)
from autogen_ext.experimental.task_centric_memory import MemoryController
from autogen_ext.experimental.task_centric_memory.utils import PageLogger
from utils import create_oai_client, load_yaml_file


"""
This code sample evaluates memory precision and recall, with no agent involved at all.
See the config file configs/retrieval.yaml for an overall view of the structure and settings in this sample,
as well as the data files used for the test.

Execute the sample with this command:
    python eval_retrieval.py configs/retrieval.yaml

This sample shows how an app can access the `MemoryController` directly
to retrieve previously stored task-insight pairs as potentially useful examplars when solving some new task.
A task is any text instruction that the app may give to an agent.
An insight is any text (like a hint, advice, a demonstration or plan) that might help the agent perform such tasks.
"""


async def eval_retrieval(
    memory_controller: MemoryController, client: ChatCompletionClient, logger: PageLogger, config: Dict[str, Any]
) -> str:
    """
    Evaluates precision and recall of task-centric memory retrieval.
    """
    logger.enter_function()

    # Load the specified data.
    task_files = config["tasks"]
    task_list = [load_yaml_file(task)["task_description"] for task in task_files]

    insight_files = config["insights"]
    insight_list = [load_yaml_file(insight)["insight"] for insight in insight_files]

    task_insight_relevance = config["task_insight_relevance"]

    # Clear memory, then store the specified task-insight pairs.
    memory_controller.reset_memory()
    for ti, task in enumerate(task_list):
        for ii, insight in enumerate(insight_list):
            if task_insight_relevance[ti][ii] == 2:
                await memory_controller.add_memo(task=task, insight=insight)

    # Test memory retrieval.
    num_retrieved = 0
    num_relevant = 0
    num_relevant_and_retrieved = 0
    for ti, task in enumerate(task_list):
        # Retrieve insights for this task.
        memos = await memory_controller.retrieve_relevant_memos(task=task)
        set_of_retrieved_insights = set(memo.insight for memo in memos)

        # Gather the insights that are relevant to this task according to ground truth.
        set_of_relevant_insights: Set[str] = set()
        for ii, insight in enumerate(insight_list):
            if task_insight_relevance[ti][ii] > 0:
                set_of_relevant_insights.add(insight)

        # Accumulate the counts.
        num_retrieved += len(set_of_retrieved_insights)
        num_relevant += len(set_of_relevant_insights)
        num_relevant_and_retrieved += len(set_of_relevant_insights & set_of_retrieved_insights)
    logger.info("\nNum retrieved:  {}".format(num_retrieved))
    logger.info("\nNum relevant:   {}".format(num_relevant))
    logger.info("\nNum relevant and retrieved:  {}".format(num_relevant_and_retrieved))

    # Compute precision and recall as percentages.
    precision = num_relevant_and_retrieved / num_retrieved if num_retrieved > 0 else 0
    recall = num_relevant_and_retrieved / num_relevant if num_relevant > 0 else 0
    precision_str = "Precision:  {:.3f}%".format(precision * 100)
    recall_str = "Recall:     {:.3f}%".format(recall * 100)
    logger.info("\n" + precision_str)
    logger.info("\n" + recall_str)

    logger.leave_function()
    return "\neval_retrieval\n" + precision_str + "\n" + recall_str


async def run_example(config_filepath: str) -> None:
    """
    Runs the code example with the necessary components.
    """
    config = load_yaml_file(config_filepath)

    # Create the necessary components.
    logger = PageLogger(config["PageLogger"])
    client = create_oai_client(config["client"])
    memory_controller = MemoryController(
        reset=True,
        client=client,
        task_assignment_callback=None,
        config=config["MemoryController"],
        logger=logger,
    )

    # Call the example function.
    results = await eval_retrieval(memory_controller, client, logger, config["test"])

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
