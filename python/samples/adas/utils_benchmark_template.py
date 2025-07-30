"""Template for benchmark-specific utility functions.

This file must contain `compute_metrics` and `load_dataset` functions.
"""

from typing import Any, Dict, List


def compute_metrics(predictions: List[Any], labels: List[Any]) -> List[float]:  # pyright: ignore
    """
    Calculates the score based on a list of predictions and labels.

    Args:
        predictions: A list of predictions that the agent system predicts
            and returns as its final answer.
        labels: A list of ground truth labels from the dataset.

    Returns:
        A list of metrics, where each corresponds to the computed score for each prediction.
    """
    pass


def load_dataset(file_path: str) -> List[Dict[str, Any]]:  # pyright: ignore
    """
    Loads in a dataset, with both input and targets, based on a file path.
    Any preprocessing, such as adding few-shot examples, must be done in this function.

    Args:
        file_path: A string representing the path of the dataset.

    Returns:
        A list of dicts, where each dict has 'input' and 'targets' keys
        corresponding to the input and ground truth labels, respectively.

        The 'input' should be a string containing the task instruction,
        (optional) few-shot contexts, and the actual input data.

        The 'output' can be of any data type. Note that this will be used
        in the `compute_metrics` function that benchmark uses.
    """
    pass
