from typing import Dict, Any
import numpy as np

from flaml.automl.task.task import (
    SUMMARIZATION,
    SEQREGRESSION,
    SEQCLASSIFICATION,
    MULTICHOICECLASSIFICATION,
    TOKENCLASSIFICATION,
)


def load_default_huggingface_metric_for_task(task):
    if task == SEQCLASSIFICATION:
        return "accuracy"
    elif task == SEQREGRESSION:
        return "r2"
    elif task == SUMMARIZATION:
        return "rouge1"
    elif task == MULTICHOICECLASSIFICATION:
        return "accuracy"
    elif task == TOKENCLASSIFICATION:
        return "seqeval"


def is_a_list_of_str(this_obj):
    return (isinstance(this_obj, list) or isinstance(this_obj, np.ndarray)) and all(
        isinstance(x, str) for x in this_obj
    )


def _clean_value(value: Any) -> str:
    if isinstance(value, float):
        return "{:.5}".format(value)
    else:
        return str(value).replace("/", "_")


def format_vars(resolved_vars: Dict) -> str:
    """Formats the resolved variable dict into a single string."""
    out = []
    for path, value in sorted(resolved_vars.items()):
        if path[0] in ["run", "env", "resources_per_trial"]:
            continue  # TrialRunner already has these in the experiment_tag
        pieces = []
        last_string = True
        for k in path[::-1]:
            if isinstance(k, int):
                pieces.append(str(k))
            elif last_string:
                last_string = False
                pieces.append(k)
        pieces.reverse()
        out.append(_clean_value("_".join(pieces)) + "=" + _clean_value(value))
    return ",".join(out)


counter = 0


def date_str():
    from datetime import datetime

    return datetime.today().strftime("%Y-%m-%d_%H-%M-%S")


def _generate_dirname(experiment_tag, trial_id):
    generated_dirname = f"train_{str(trial_id)}_{experiment_tag}"
    generated_dirname = generated_dirname[:130]
    generated_dirname += f"_{date_str()}"
    return generated_dirname.replace("/", "_")


def get_logdir_name(dirname, local_dir):
    import os

    local_dir = os.path.expanduser(local_dir)
    logdir = os.path.join(local_dir, dirname)
    return logdir


class Counter:
    counter = 0

    @staticmethod
    def get_trial_fold_name(local_dir, trial_config, trial_id):
        Counter.counter += 1
        experiment_tag = "{0}_{1}".format(str(Counter.counter), format_vars(trial_config))
        logdir = get_logdir_name(_generate_dirname(experiment_tag, trial_id=trial_id), local_dir)
        return logdir


class LabelEncoderforTokenClassification:
    def fit_transform(self, y):
        # if the labels are tokens, convert them to ids
        if any(isinstance(id, str) for id in y[0]):
            self.label_list = sorted(list(set().union(*y)))
            self._tokenlabel_to_id = {self.label_list[id]: id for id in range(len(self.label_list))}
            y = y.apply(lambda sent: [self._tokenlabel_to_id[token] for token in sent])
        # if the labels are not tokens, they must be ids
        else:
            assert all(isinstance(id, (int, np.integer)) for id in y[0]), "The labels must either be tokens or ids"
        return y

    def transform(self, y):
        if hasattr(self, "_tokenlabel_to_id"):
            y = y.apply(lambda sent: [self._tokenlabel_to_id[token] for token in sent])
        return y
