import os
import pickle
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TypedDict

from ._string_similarity_map import StringSimilarityMap
from .utils.page_logger import PageLogger


@dataclass
class Memo:
    """
    Represents an atomic unit of memory that can be stored in a memory bank and later retrieved.
    """

    task: str | None  # The task description, if any.
    insight: str  # A hint, solution, plan, or any other text that may help solve a similar task.


# Following the nested-config pattern, this TypedDict minimizes code changes by encapsulating
# the settings that change frequently, as when loading many settings from a single YAML file.
class MemoryBankConfig(TypedDict, total=False):
    path: str
    relevance_conversion_threshold: float
    n_results: int
    distance_threshold: int


class MemoryBank:
    """
    Stores task-completion insights as memories in a vector DB for later retrieval.

    Args:
        reset: True to clear the DB before starting.
        config: An optional dict that can be used to override the following values:

            - path: The path to the directory where the memory bank files are stored.
            - relevance_conversion_threshold: The threshold used to normalize relevance.
            - n_results: The maximum number of most relevant results to return for any given topic.
            - distance_threshold: The maximum string-pair distance for a memo to be retrieved.

        logger: An optional logger. If None, no logging will be performed.
    """

    def __init__(
        self,
        reset: bool,
        config: MemoryBankConfig | None = None,
        logger: PageLogger | None = None,
    ) -> None:
        if logger is None:
            logger = PageLogger()  # Nothing will be logged by this object.
        self.logger = logger
        self.logger.enter_function()

        # Apply default settings and any config overrides.
        memory_dir_path = "./memory_bank/default"
        self.relevance_conversion_threshold = 1.7
        self.n_results = 25
        self.distance_threshold = 100
        if config is not None:
            memory_dir_path = config.get("path", memory_dir_path)
            self.relevance_conversion_threshold = config.get(
                "relevance_conversion_threshold", self.relevance_conversion_threshold
            )
            self.n_results = config.get("n_results", self.n_results)
            self.distance_threshold = config.get("distance_threshold", self.distance_threshold)

        memory_dir_path = os.path.expanduser(memory_dir_path)
        self.logger.info("\nMEMORY BANK DIRECTORY  {}".format(memory_dir_path))
        path_to_db_dir = os.path.join(memory_dir_path, "string_map")
        self.path_to_dict = os.path.join(memory_dir_path, "uid_memo_dict.pkl")

        self.string_map = StringSimilarityMap(reset=reset, path_to_db_dir=path_to_db_dir, logger=self.logger)

        # Load or create the associated memo dict on disk.
        self.uid_memo_dict: Dict[str, Memo] = {}
        self.last_memo_id = 0
        if (not reset) and os.path.exists(self.path_to_dict):
            self.logger.info("\nLOADING MEMOS FROM DISK  at {}".format(self.path_to_dict))
            with open(self.path_to_dict, "rb") as f:
                self.uid_memo_dict = pickle.load(f)
                self.last_memo_id = len(self.uid_memo_dict)
                self.logger.info("\n{} MEMOS LOADED".format(len(self.uid_memo_dict)))

        # Clear the DB if requested.
        if reset:
            self._reset_memos()

        self.logger.leave_function()

    def reset(self) -> None:
        """
        Forces immediate deletion of all contents, in memory and on disk.
        """
        self.string_map.reset_db()
        self._reset_memos()

    def _reset_memos(self) -> None:
        """
        Forces immediate deletion of the memos, in memory and on disk.
        """
        self.logger.info("\nCLEARING MEMOS")
        self.uid_memo_dict = {}
        self.save_memos()

    def save_memos(self) -> None:
        """
        Saves the current memo structures (possibly empty) to disk.
        """
        self.string_map.save_string_pairs()
        with open(self.path_to_dict, "wb") as file:
            self.logger.info("\nSAVING MEMOS TO DISK  at {}".format(self.path_to_dict))
            pickle.dump(self.uid_memo_dict, file)

    def contains_memos(self) -> bool:
        """
        Returns True if the memory bank contains any memo.
        """
        return len(self.uid_memo_dict) > 0

    def _map_topics_to_memo(self, topics: List[str], memo_id: str, memo: Memo) -> None:
        """
        Adds a mapping in the vec DB from each topic to the memo.
        """
        self.logger.enter_function()
        self.logger.info("\nINSIGHT\n{}".format(memo.insight))
        for topic in topics:
            self.logger.info("\n TOPIC = {}".format(topic))
            self.string_map.add_input_output_pair(topic, memo_id)
        self.uid_memo_dict[memo_id] = memo
        self.save_memos()
        self.logger.leave_function()

    def add_memo(self, insight_str: str, topics: List[str], task_str: Optional[str] = None) -> None:
        """
        Adds an insight to the memory bank, given topics related to the insight, and optionally the task.
        """
        self.logger.enter_function()
        self.last_memo_id += 1
        id_str = str(self.last_memo_id)
        insight = Memo(insight=insight_str, task=task_str)
        self._map_topics_to_memo(topics, id_str, insight)
        self.logger.leave_function()

    def add_task_with_solution(self, task: str, solution: str, topics: List[str]) -> None:
        """
        Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        This is useful when the insight is a demonstration of how to solve a given type of task.
        """
        self.logger.enter_function()
        self.last_memo_id += 1
        id_str = str(self.last_memo_id)
        # Prepend the insight to the task description for context.
        insight_str = "Example task:\n\n{}\n\nExample solution:\n\n{}".format(task, solution)
        memo = Memo(insight=insight_str, task=task)
        self._map_topics_to_memo(topics, id_str, memo)
        self.logger.leave_function()

    def get_relevant_memos(self, topics: List[str]) -> List[Memo]:
        """
        Returns any memos from the memory bank that appear sufficiently relevant to the input topics.
        """
        self.logger.enter_function()

        # Retrieve all topic matches, and gather them into a single list.
        matches: List[Tuple[str, str, float]] = []  # Each match is a tuple: (topic, memo_id, distance)
        for topic in topics:
            matches.extend(self.string_map.get_related_string_pairs(topic, self.n_results, self.distance_threshold))

        # Build a dict of memo-relevance pairs from the matches.
        memo_relevance_dict: Dict[str, float] = {}
        for match in matches:
            relevance = self.relevance_conversion_threshold - match[2]
            memo_id = match[1]
            if memo_id in memo_relevance_dict:
                memo_relevance_dict[memo_id] += relevance
            else:
                memo_relevance_dict[memo_id] = relevance

        # Log the details of all the retrieved memos.
        self.logger.info("\n{} POTENTIALLY RELEVANT MEMOS".format(len(memo_relevance_dict)))
        for memo_id, relevance in memo_relevance_dict.items():
            memo = self.uid_memo_dict[memo_id]
            details = ""
            if memo.task is not None:
                details += "\n  TASK: {}\n".format(memo.task)
            details += "\n  INSIGHT: {}\n\n  RELEVANCE: {:.3f}\n".format(memo.insight, relevance)
            self.logger.info(details)

        # Sort the memo-relevance pairs by relevance, in descending order.
        memo_relevance_dict = dict(sorted(memo_relevance_dict.items(), key=lambda item: item[1], reverse=True))

        # Compose the list of sufficiently relevant memos to return.
        memo_list: List[Memo] = []
        for memo_id in memo_relevance_dict:
            if memo_relevance_dict[memo_id] >= 0:
                memo_list.append(self.uid_memo_dict[memo_id])

        self.logger.leave_function()
        return memo_list
