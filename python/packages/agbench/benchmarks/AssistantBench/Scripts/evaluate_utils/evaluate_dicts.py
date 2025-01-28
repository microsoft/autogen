# From AssistantBench modified slightly.
from typing import Dict, List
import numpy as np

from .utils import _align_bags


def calculate_f1_score(precision, recall):
    if precision + recall == 0:
        return 0  # Handle the case to avoid division by zero
    return 2 * (precision * recall) / (precision + recall)


def calc_recall(pred: Dict, gold: Dict, use_gold_for_eval: bool):
    from .evaluate_factory import get_evaluator_from_gold_answer

    recall = []
    for gold_key, gold_value in gold.items():
        pred_value = pred.get(gold_key)
        gold_value = fix_number(gold_value)
        pred_value = fix_number(pred_value)
        if gold_key not in pred:
            recall.append(0)
        else:
            evaluator = (
                get_evaluator_from_gold_answer(type(gold_value))
                if use_gold_for_eval
                else get_evaluator_from_gold_answer(type(pred_value))
            )
            if type(pred_value) != type(gold_value):
                recall.append(0)
                continue
            recall.append(evaluator(pred_value, gold_value))
    avg_recall = np.average(recall)
    return avg_recall


def fix_number(number):
    if type(number) == str:
        copy_ans = number
        copy_ans = " ".join(
            " ".join(" ".join(copy_ans.split("$")).split("%")).split("sqft")
        ).strip()
        copy_ans = copy_ans.strip()
        copy_ans = copy_ans.replace(",", ".")
        try:
            return float(copy_ans)
        except:
            return number
    elif type(number) == int:
        return float(number)
    else:
        return number


def evaluate_pair_of_dicts(pred: Dict, gold: Dict):
    recall = calc_recall(pred, gold, True)
    precision = calc_recall(gold, pred, False)
    f1 = calculate_f1_score(precision, recall)
    return f1


def evaluate_dicts(pred: List[Dict], gold: List[Dict]):
    if not (
        type(pred) == dict
        or len(pred) == 0
        or (type(pred) == list and type(pred[0]) == dict)
    ):
        return 0
    max_alignment_scores = _align_bags(pred, gold, evaluate_pair_of_dicts)
    return np.average(max_alignment_scores)
