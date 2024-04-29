import logging
from typing import Any, Dict, List

from termcolor import colored

from .base import QueryResults


class ColoredLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def debug(self, msg, *args, color=None, **kwargs):
        super().debug(colored(msg, color), *args, **kwargs)

    def info(self, msg, *args, color=None, **kwargs):
        super().info(colored(msg, color), *args, **kwargs)

    def warning(self, msg, *args, color="yellow", **kwargs):
        super().warning(colored(msg, color), *args, **kwargs)

    def error(self, msg, *args, color="light_red", **kwargs):
        super().error(colored(msg, color), *args, **kwargs)

    def critical(self, msg, *args, color="red", **kwargs):
        super().critical(colored(msg, color), *args, **kwargs)

    def fatal(self, msg, *args, color="red", **kwargs):
        super().fatal(colored(msg, color), *args, **kwargs)


def get_logger(name: str, level: int = logging.INFO) -> ColoredLogger:
    logger = ColoredLogger(name, level)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.handlers[0].setFormatter(formatter)
    return logger


logger = get_logger(__name__)


def filter_results_by_distance(results: QueryResults, distance_threshold: float = -1) -> QueryResults:
    """Filters results based on a distance threshold.

    Args:
        results: QueryResults | The query results. List[List[Tuple[Document, float]]]
        distance_threshold: The maximum distance allowed for results.

    Returns:
        QueryResults | A filtered results containing only distances smaller than the threshold.
    """

    if distance_threshold > 0:
        results = [[(key, value) for key, value in data if value < distance_threshold] for data in results]

    return results


def chroma_results_to_query_results(data_dict: Dict[str, List[List[Any]]], special_key="distances") -> QueryResults:
    """Converts a dictionary with list-of-list values to a list of tuples.

    Args:
        data_dict: A dictionary where keys map to lists of lists or None.
        special_key: The key in the dictionary containing the special values
                    for each tuple.

    Returns:
        A list of tuples, where each tuple contains a sub-dictionary with
        some keys from the original dictionary and the value from the
        special_key.

    Example:
        data_dict = {
            "key1s": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            "key2s": [["a", "b", "c"], ["c", "d", "e"], ["e", "f", "g"]],
            "key3s": None,
            "key4s": [["x", "y", "z"], ["1", "2", "3"], ["4", "5", "6"]],
            "distances": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
        }

        results = [
            [
                ({"key1": 1, "key2": "a", "key4": "x"}, 0.1),
                ({"key1": 2, "key2": "b", "key4": "y"}, 0.2),
                ({"key1": 3, "key2": "c", "key4": "z"}, 0.3),
            ],
            [
                ({"key1": 4, "key2": "c", "key4": "1"}, 0.4),
                ({"key1": 5, "key2": "d", "key4": "2"}, 0.5),
                ({"key1": 6, "key2": "e", "key4": "3"}, 0.6),
            ],
            [
                ({"key1": 7, "key2": "e", "key4": "4"}, 0.7),
                ({"key1": 8, "key2": "f", "key4": "5"}, 0.8),
                ({"key1": 9, "key2": "g", "key4": "6"}, 0.9),
            ],
        ]
    """

    keys = [key for key in data_dict if key != special_key]
    result = []

    for i in range(len(data_dict[special_key])):
        sub_result = []
        for j, distance in enumerate(data_dict[special_key][i]):
            sub_dict = {}
            for key in keys:
                if data_dict[key] is not None and len(data_dict[key]) > i:
                    sub_dict[key[:-1]] = data_dict[key][i][j]  # remove 's' in the end from key
            sub_result.append((sub_dict, distance))
        result.append(sub_result)

    return result
