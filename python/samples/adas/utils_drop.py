"""Utility file for DROP benchmark.

https://github.com/openai/simple-evals/blob/main/drop_eval.py

DROP: A Reading Comprehension Benchmark Requiring Discrete Reasoning Over Paragraphs
Dheeru Dua, Yizhong Wang, Pradeep Dasigi, Gabriel Stanovsky, Sameer Singh, Matt Gardner
https://arxiv.org/abs/1903.00161
"""
# pyright: basic

import gzip
import json
import re
import string
from typing import Any, Dict, List, Set, Tuple, Union

import numpy as np
from scipy.optimize import linear_sum_assignment


def _remove_articles(text: str) -> str:
    regex = re.compile(r"\b(a|an|the)\b", re.UNICODE)
    return re.sub(regex, " ", text)


def _white_space_fix(text: str) -> str:
    return " ".join(text.split())


EXCLUDE = set(string.punctuation)


def _remove_punc(text: str) -> str:
    if not _is_number(text):
        return "".join(ch for ch in text if ch not in EXCLUDE)
    else:
        return text


def _lower(text: str) -> str:
    return text.lower()


def _tokenize(text: str) -> List[str]:
    return re.split(" |-", text)


def _normalize_answer(text: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""

    parts = [
        _white_space_fix(_remove_articles(_normalize_number(_remove_punc(_lower(token))))) for token in _tokenize(text)
    ]
    parts = [part for part in parts if part.strip()]
    normalized = " ".join(parts).strip()
    return normalized


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def _normalize_number(text: str) -> str:
    if _is_number(text):
        return str(float(text))
    else:
        return text


def _answer_to_bags(answer: Union[str, List[str], Tuple[str, ...]]) -> Tuple[List[str], List[Set[str]]]:
    if isinstance(answer, (list, tuple)):
        raw_spans = answer
    else:
        raw_spans = [answer]
    normalized_spans: List[str] = []
    token_bags = []
    for raw_span in raw_spans:
        normalized_span = _normalize_answer(raw_span)
        normalized_spans.append(normalized_span)
        token_bags.append(set(normalized_span.split()))
    return normalized_spans, token_bags


def _align_bags(predicted: List[Set[str]], gold: List[Set[str]]):
    """
    Takes gold and predicted answer sets and first finds the optimal 1-1 alignment
    between them and gets maximum metric values over all the answers.
    """
    scores = np.zeros([len(gold), len(predicted)])
    for gold_index, gold_item in enumerate(gold):
        for pred_index, pred_item in enumerate(predicted):
            if _match_numbers_if_present(gold_item, pred_item):
                scores[gold_index, pred_index] = _compute_f1(pred_item, gold_item)
    row_ind, col_ind = linear_sum_assignment(-scores)

    max_scores = np.zeros([max(len(gold), len(predicted))])
    for row, column in zip(row_ind, col_ind, strict=False):
        max_scores[row] = max(max_scores[row], scores[row, column])  # pyright: ignore
    return max_scores


def _compute_f1(predicted_bag: Set[str], gold_bag: Set[str]) -> float:
    intersection = len(gold_bag.intersection(predicted_bag))
    if not predicted_bag:
        precision = 1.0
    else:
        precision = intersection / float(len(predicted_bag))
    if not gold_bag:
        recall = 1.0
    else:
        recall = intersection / float(len(gold_bag))
    f1 = ((2 * precision * recall) / (precision + recall) if not (precision == 0.0 and recall == 0.0) else 0.0) * 100
    return f1


def _match_numbers_if_present(gold_bag: Set[str], predicted_bag: Set[str]) -> bool:
    gold_numbers = set()
    predicted_numbers = set()
    for word in gold_bag:
        if _is_number(word):
            gold_numbers.add(word)
    for word in predicted_bag:
        if _is_number(word):
            predicted_numbers.add(word)
    if (not gold_numbers) or gold_numbers.intersection(predicted_numbers):
        return True
    return False


def get_drop_metrics(
    predicted: Union[str, List[str], Tuple[str, ...]], gold: Union[str, List[str], Tuple[str, ...]]
) -> Tuple[float, float]:
    """
    Takes a predicted answer and a gold answer (that are both either a string or a list of
    strings), and returns exact match and the DROP F1 metric for the prediction.  If you are
    writing a script for evaluating objects in memory (say, the output of predictions during
    validation, or while training), this is the function you want to call, after using
    :func:`answer_json_to_strings` when reading the gold answer from the released data file.
    """
    predicted_bags = _answer_to_bags(predicted)
    gold_bags = _answer_to_bags(gold)

    if set(predicted_bags[0]) == set(gold_bags[0]) and len(predicted_bags[0]) == len(gold_bags[0]):
        exact_match = 1.0
    else:
        exact_match = 0.0

    f1_per_bag = _align_bags(predicted_bags[1], gold_bags[1])
    f1 = np.mean(f1_per_bag)
    f1 = round(f1, 2)
    return exact_match, f1  # pyright: ignore


def answer_json_to_strings(answer: Dict[str, Any]) -> Tuple[Tuple[str, ...], str]:
    """
    Takes an answer JSON blob from the DROP data release and converts it into strings used for
    evaluation.
    """
    if "number" in answer and answer["number"]:
        return tuple([str(answer["number"])]), "number"
    elif "spans" in answer and answer["spans"]:
        return tuple(answer["spans"]), "span" if len(answer["spans"]) == 1 else "spans"
    elif "date" in answer:
        return (
            tuple(
                ["{0} {1} {2}".format(answer["date"]["day"], answer["date"]["month"], answer["date"]["year"]).strip()]
            ),
            "date",
        )
    else:
        raise ValueError(f"Answer type not found, should be one of number, spans or date at: {json.dumps(answer)}")


def answer_json_to_string(answer_json):
    return json.dumps(answer_json_to_strings(answer_json))


def normalize(s: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""
    s = s.lower()
    exclude = set(string.punctuation)
    s = "".join(char for char in s if char not in exclude)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = " ".join(s.split())
    return s


def fuzzy_match(s1: str, s2: str) -> bool:
    s1 = normalize(s1)
    s2 = normalize(s2)

    if s1 == "" or s2 == "":
        return s1 == s2

    return s1 in s2 or s2 in s1


def compute_drop_metrics(sample: str, reference: list[str]) -> Tuple[float, float]:
    em_scores = []
    f1_scores = []
    for answer in reference:
        if answer.strip() != "":
            em, f1 = get_drop_metrics(sample, answer)
            em_scores.append(em)
            f1_scores.append(f1)
    return (max(em_scores), max(f1_scores))


def compute_metrics(predictions: List[Any], labels: List[Any]) -> List[float]:
    """
    Calculates the score based on a list of predictions and labels.

    Args:
        predictions: A list of predictions that the agent system predicts
            and returns as its final answer.
        labels: A list of ground truth labels from the dataset.

    Returns:
        A list of metrics, where each corresponds to the computed score for each prediction.
    """
    acc_list = []
    for q_idx, res in enumerate(predictions):
        try:
            correct_answers = labels[q_idx]
            print(f"extracted_answer {res}, correct_answers {correct_answers}")
            em_score, f1_score = compute_drop_metrics(res, correct_answers)
        except Exception:
            acc_list.append(0)
            continue

        acc_list.append(f1_score)
    return acc_list


def load_dataset(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads in a dataset, with both input and targets, based on a file path.

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
    with gzip.open(file_path, mode="rb") as f:
        test_samples = [json.loads(line) for line in f]
    few_shot_prompt = """You will be asked to read a passage and answer a question.

# Examples:
Passage: As of the census of 2000, there were 952 people, 392 households, and 241 families residing in the village. The population density was 952.9 people per square mile (367.6/km²). There were 449 housing units at an average density of 449.4 per square mile (173.4/km²). The racial makeup of the village was 96.11% White (U.S. Census), 0.95% African American (U.S. Census) or Race (United States Census), 0.11% Native American (U.S. Census), 0.11% Asian (U.S. Census), 0.21% from Race (United States Census), and 2.52% from two or more races. 1.05% of the population were Hispanics in the United States or Latino (U.S. Census) of any race.\nQuestion: How many more people, in terms of percentage, were from two or more races compared to being solely Native American or solely Asian?\nAnswer: 2.3

# Your Task
---

"""
    examples = []
    for sample in test_samples:
        sample["inputs"] = few_shot_prompt + sample["context"]
        sample["targets"] = sample["ref_text"].split("|")
        examples.append(sample)
    return examples
