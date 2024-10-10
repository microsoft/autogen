from typing import List, Set, Tuple, Union, Callable
import numpy as np
from scipy.optimize import linear_sum_assignment


def _align_bags(
    predicted: List[Set[str]],
    gold: List[Set[str]],
    method: Callable[[object, object], float],
) -> List[float]:
    """
    Takes gold and predicted answer sets and first finds the optimal 1-1 alignment
    between them and gets maximum metric values over all the answers.
    """
    scores = np.zeros([len(gold), len(predicted)])
    for gold_index, gold_item in enumerate(gold):
        for pred_index, pred_item in enumerate(predicted):
            scores[gold_index, pred_index] = method(pred_item, gold_item)
    row_ind, col_ind = linear_sum_assignment(-scores)

    max_scores = np.zeros([max(len(gold), len(predicted))])
    for row, column in zip(row_ind, col_ind):
        max_scores[row] = max(max_scores[row], scores[row, column])
    return max_scores
