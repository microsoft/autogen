import os
import pickle
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ._string_similarity_map import StringSimilarityMap
from .page_logger import PageLogger


@dataclass
class Insight:
    """
    Represents a task-completion insight, which is a string that may help solve a task.
    """

    id: str
    insight_str: str
    task_str: str | None
    topics: List[str]


class AgenticMemoryBank:
    """
    Stores task-completion insights in a vector DB for later retrieval.

    Args:
        - settings: Settings for the memory bank.
        - reset: True to clear the DB before starting.
        - logger: The PageLogger object to use for logging.

    Methods:
        - reset: Forces immediate deletion of all contents, in memory and on disk.
        - save_insights: Saves the current insight structures (possibly empty) to disk.
        - contains_insights: Returns True if the memory bank contains any insights.
        - add_insight: Adds an insight to the memory bank, given topics related to the insight, and optionally the task.
        - add_task_with_solution: Adds a task-insight pair to the memory bank, to be retrieved together later.
        - get_relevant_insights: Returns any insights from the memory bank that appear sufficiently relevant to the given
    """

    def __init__(self, settings: Dict[str, Any], reset: bool, logger: PageLogger) -> None:
        self.settings = settings
        self.logger = logger
        self.logger.enter_function()

        memory_dir_path = os.path.expanduser(self.settings["path"])
        self.relevance_conversion_threshold = self.settings["relevance_conversion_threshold"]
        self.n_results = self.settings["n_results"]
        self.distance_threshold = self.settings["distance_threshold"]

        path_to_db_dir = os.path.join(memory_dir_path, "string_map")
        self.path_to_dict = os.path.join(memory_dir_path, "uid_insight_dict.pkl")

        self.string_map = StringSimilarityMap(reset=reset, path_to_db_dir=path_to_db_dir, logger=self.logger)

        # Load or create the associated insight dict on disk.
        self.uid_insight_dict: Dict[str, Insight] = {}
        self.last_insight_id = 0
        if (not reset) and os.path.exists(self.path_to_dict):
            self.logger.info("\nLOADING INSIGHTS FROM DISK  {}".format(self.path_to_dict))
            self.logger.info("    Location = {}".format(self.path_to_dict))
            with open(self.path_to_dict, "rb") as f:
                self.uid_insight_dict = pickle.load(f)
                self.last_insight_id = len(self.uid_insight_dict)
                self.logger.info("\n{} INSIGHTS LOADED".format(len(self.uid_insight_dict)))

        # Clear the DB if requested.
        if reset:
            self._reset_insights()

        self.logger.leave_function()

    def reset(self) -> None:
        """
        Forces immediate deletion of all contents, in memory and on disk.
        """
        self.string_map.reset_db()
        self._reset_insights()

    def _reset_insights(self) -> None:
        """
        Forces immediate deletion of the insights, in memory and on disk.
        """
        self.uid_insight_dict = {}
        self.save_insights()

    def save_insights(self) -> None:
        """
        Saves the current insight structures (possibly empty) to disk.
        """
        self.string_map.save_string_pairs()
        with open(self.path_to_dict, "wb") as file:
            pickle.dump(self.uid_insight_dict, file)

    def contains_insights(self) -> bool:
        """
        Returns True if the memory bank contains any insights.
        """
        return len(self.uid_insight_dict) > 0

    def _map_topics_to_insight(self, topics: List[str], insight_id: str, insight: Insight) -> None:
        """
        Adds a mapping in the vec DB from each topic to the insight.
        """
        self.logger.enter_function()
        self.logger.info("\nINSIGHT\n{}".format(insight.insight_str))
        for topic in topics:
            self.logger.info("\n TOPIC = {}".format(topic))
            self.string_map.add_input_output_pair(topic, insight_id)
        self.uid_insight_dict[insight_id] = insight
        self.logger.leave_function()

    def add_insight(self, insight_str: str, topics: List[str], task_str: Optional[str] = None) -> None:
        """
        Adds an insight to the memory bank, given topics related to the insight, and optionally the task.
        """
        self.last_insight_id += 1
        id_str = str(self.last_insight_id)
        insight = Insight(id=id_str, insight_str=insight_str, task_str=task_str, topics=topics)
        self._map_topics_to_insight(topics, id_str, insight)

    def add_task_with_solution(self, task: str, solution: str, topics: List[str]) -> None:
        """
        Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        This is useful when the insight is a demonstration of how to solve a given type of task.
        """
        self.last_insight_id += 1
        id_str = str(self.last_insight_id)
        # Prepend the insight to the task description for context.
        insight_str = "Example task:\n\n{}\n\nExample solution:\n\n{}".format(task, solution)
        insight = Insight(id=id_str, insight_str=insight_str, task_str=task, topics=topics)
        self._map_topics_to_insight(topics, id_str, insight)

    def get_relevant_insights(self, task_topics: List[str]) -> Dict[str, float]:
        """
        Returns any insights from the memory bank that appear sufficiently relevant to the given task topics.
        """
        # Process the matching topics to build a dict of insight-relevance pairs.
        matches: List[Tuple[str, str, float]] = []  # Each match is a tuple: (topic, insight, distance)
        insight_relevance_dict: Dict[str, float] = {}
        for topic in task_topics:
            matches.extend(self.string_map.get_related_string_pairs(topic, self.n_results, self.distance_threshold))
        for match in matches:
            relevance = self.relevance_conversion_threshold - match[2]
            insight_id = match[1]
            insight_str = self.uid_insight_dict[insight_id].insight_str
            if insight_str in insight_relevance_dict:
                insight_relevance_dict[insight_str] += relevance
            else:
                insight_relevance_dict[insight_str] = relevance

        # Filter out insights with overall relevance below zero.
        for insight in list(insight_relevance_dict.keys()):
            if insight_relevance_dict[insight] < 0:
                del insight_relevance_dict[insight]

        return insight_relevance_dict
