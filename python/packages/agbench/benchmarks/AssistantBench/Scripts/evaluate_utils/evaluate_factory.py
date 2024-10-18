#From AssistantBench modified slightly.

from typing import Union, Dict

from .evaluate_dicts import evaluate_dicts
from .evaluate_numbers import evaluate_numbers
from .evaluate_strings import evaluate_strings

EvaluatorFactory = {
    "string": evaluate_strings,
    "number": evaluate_numbers,
    "json": evaluate_dicts,
    "string list": evaluate_strings,
}

EvaluatorFactoryFromType = {
    str: evaluate_strings,
    int: evaluate_numbers,
    float: evaluate_numbers,
    bool: evaluate_strings,
    list: evaluate_strings,
}


def get_evaluator(evaluator: str):
    return EvaluatorFactory[evaluator]


def get_evaluator_from_gold_answer(gold_answer: Union[str, int, float]):
    return EvaluatorFactoryFromType[gold_answer]
