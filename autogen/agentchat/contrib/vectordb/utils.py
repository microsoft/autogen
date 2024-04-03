from typing import List, Dict
import logging
from termcolor import colored


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


def get_logger(name: str, level: int = logging.INFO) -> ColoredLogger:
    logger = ColoredLogger(name, level)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)5d - %(levelname)s - %(message)s")
    logger.handlers[0].setFormatter(formatter)
    return logger


logger = get_logger(__name__)


def filter_results_by_distance(
    results: Dict[str, List[List[Dict]]], distance_threshold: float = -1
) -> Dict[str, List[List[Dict]]]:
    """Filters results based on a distance threshold.

    Args:
        results: A dictionary containing results to be filtered.
        distance_threshold: The maximum distance allowed for results.

    Returns:
        Dict[str, List[List[Dict]]] | A filtered dictionary containing only results within the threshold.
    """

    if distance_threshold > 0:
        # Filter distances first:
        return_ridx = [
            [ridx for ridx, distance in enumerate(distances) if distance < distance_threshold]
            for distances in results["distances"]
        ]

        # Filter other keys based on filtered distances:
        results = {
            key: [
                [value for ridx, value in enumerate(results_list) if ridx in return_ridx[qidx]]
                for qidx, results_list in enumerate(results_lists)
            ]
            for key, results_lists in results.items()
        }

    return results
