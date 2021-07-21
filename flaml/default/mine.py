from typing import List, Tuple, Callable, Optional
from numpy.typing import ArrayLike


class Task:
    name: str
    input: dict          # input to automl
    metadata: ArrayLike  # featurized metadata


def mine_defaults(
    tasks: List[Task],
    regret_bound: float,
    config_predictor: Optional[Callable[[ArrayLike], dict]] = None,
) -> Tuple[Callable[[ArrayLike], dict], List[float]]:
    '''
    Args:
        tasks: List[Task] | benchmark tasks
        regret_bound: float | maximal regret desired
        config_predictor: None or Callable[[ArrayLike], dict] |
            The existing task -> config predictor

    Returns:
        config_predictor: Callable[[ArrayLike], dict] |
            The new task -> config predictor
        regret: List[float] | the regret on each task
    '''
    pass
