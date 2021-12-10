import argparse
from dataclasses import dataclass, field
from typing import Dict, Any

from ..data import (
    SUMMARIZATION,
    SEQREGRESSION,
    SEQCLASSIFICATION,
    NLG_TASKS
)


def load_default_huggingface_metric_for_task(task):
    from ..data import SEQCLASSIFICATION, SEQREGRESSION

    if task == SEQCLASSIFICATION:
        return "accuracy"
    elif task == SEQREGRESSION:
        return "rmse"
    elif task == SUMMARIZATION:
        return "rouge"
    # TODO: elif task == your task, return the default metric name for your task,
    #  e.g., if task == MULTIPLECHOICE, return "accuracy"
    #  notice this metric name has to be in ['accuracy', 'bertscore', 'bleu', 'bleurt',
    #  'cer', 'chrf', 'code_eval', 'comet', 'competition_math', 'coval', 'cuad',
    #  'f1', 'gleu', 'glue', 'google_bleu', 'indic_glue', 'matthews_correlation',
    #  'meteor', 'pearsonr', 'precision', 'recall', 'rouge', 'sacrebleu', 'sari',
    #  'seqeval', 'spearmanr', 'squad', 'squad_v2', 'super_glue', 'ter', 'wer',
    #  'wiki_split', 'xnli']


global tokenized_column_names


def tokenize_text(X, task, custom_hpo_task):
    from ..data import SEQCLASSIFICATION, SEQREGRESSION

    if task in (SEQCLASSIFICATION, SEQREGRESSION):
        return tokenize_text_seqclassification(X, custom_hpo_task)
    # TODO: elif task == your task, return the tokenized result
    #  for example, if your task == MULTIPLE CHOICE, you should
    #  create a function named tokenize_text_multiplechoice(X, custom_hpo_args)
    #  and what it does is the same as preprocess_function at
    #  https://github.com/huggingface/transformers/blob/master/examples/pytorch/multiple-choice/run_swag.py#L329


def tokenize_text_seqclassification(X, custom_hpo_args):
    from transformers import AutoTokenizer
    import pandas

    global tokenized_column_names

    this_tokenizer = AutoTokenizer.from_pretrained(
        custom_hpo_args.model_path, use_fast=True
    )
    d = X.apply(
        lambda x: tokenize_glue(x, this_tokenizer, custom_hpo_args),
        axis=1,
        result_type="expand",
    )
    X_tokenized = pandas.DataFrame(columns=tokenized_column_names)
    X_tokenized[tokenized_column_names] = d
    return X_tokenized


def tokenize_glue(this_row, this_tokenizer, custom_hpo_args):
    global tokenized_column_names
    assert (
        "max_seq_length" in custom_hpo_args.__dict__
    ), "max_seq_length must be provided for glue"

    tokenized_example = this_tokenizer(
        *tuple(this_row),
        padding="max_length",
        max_length=custom_hpo_args.max_seq_length,
        truncation=True,
    )
    tokenized_column_names = sorted(tokenized_example.keys())
    return [tokenized_example[x] for x in tokenized_column_names]


def separate_config(config):
    from transformers import TrainingArguments

    training_args_config = {}
    per_model_config = {}

    for key, val in config.items():
        if key in TrainingArguments.__dict__:
            training_args_config[key] = val
        else:
            per_model_config[key] = val

    return training_args_config, per_model_config


def get_num_labels(task, y_train):
    from ..data import SEQCLASSIFICATION, SEQREGRESSION

    if task == SEQREGRESSION:
        return 1
    elif task == SEQCLASSIFICATION:
        return len(set(y_train))
    else:
        return None


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


def get_trial_fold_name(local_dir, trial_config, trial_id):
    global counter
    counter = counter + 1
    experiment_tag = "{0}_{1}".format(str(counter), format_vars(trial_config))
    logdir = get_logdir_name(
        _generate_dirname(experiment_tag, trial_id=trial_id), local_dir
    )
    return logdir


def load_model(checkpoint_path, task, num_labels, per_model_config=None):
    from transformers import AutoConfig
    from .huggingface.switch_head_auto import (
        AutoSeqClassificationHead,
        MODEL_CLASSIFICATION_HEAD_MAPPING,
    )
    from ..data import SEQCLASSIFICATION, SEQREGRESSION

    this_model_type = AutoConfig.from_pretrained(checkpoint_path).model_type
    this_vocab_size = AutoConfig.from_pretrained(checkpoint_path).vocab_size

    def get_this_model():
        from transformers import AutoModelForSequenceClassification

        if task in (SEQCLASSIFICATION, SEQREGRESSION):
            return AutoModelForSequenceClassification.from_pretrained(
                checkpoint_path, config=model_config
            )
        # TODO: elif task == your task, fill in the line in your transformers example
        #  that loads the model, e.g., if task == MULTIPLE CHOICE, according to
        #  https://github.com/huggingface/transformers/blob/master/examples/pytorch/multiple-choice/run_swag.py#L298
        #  you can return AutoModelForMultipleChoice.from_pretrained(checkpoint_path, config=model_config)

    def is_pretrained_model_in_classification_head_list(model_type):
        return model_type in MODEL_CLASSIFICATION_HEAD_MAPPING

    def _set_model_config(checkpoint_path):
        if task in (SEQCLASSIFICATION, SEQREGRESSION):
            if per_model_config and len(per_model_config) > 0:
                model_config = AutoConfig.from_pretrained(
                    checkpoint_path,
                    num_labels=model_config_num_labels,
                    **per_model_config,
                )
            else:
                model_config = AutoConfig.from_pretrained(
                    checkpoint_path, num_labels=model_config_num_labels
                )
            return model_config
        # TODO: elif task == your task, uncomment the code below:
        # else:
        #     if per_model_config and len(per_model_config) > 0:
        #         model_config = AutoConfig.from_pretrained(
        #             checkpoint_path,
        #             **per_model_config,
        #         )
        #     else:
        #         model_config = AutoConfig.from_pretrained(
        #             checkpoint_path
        #         )
        #     return model_config

    if task == SEQCLASSIFICATION:
        num_labels_old = AutoConfig.from_pretrained(checkpoint_path).num_labels
        if is_pretrained_model_in_classification_head_list(this_model_type):
            model_config_num_labels = num_labels_old
        else:
            model_config_num_labels = num_labels
        model_config = _set_model_config(checkpoint_path)

        if is_pretrained_model_in_classification_head_list(this_model_type):
            if num_labels != num_labels_old:
                this_model = get_this_model()
                model_config.num_labels = num_labels
                this_model.num_labels = num_labels
                this_model.classifier = (
                    AutoSeqClassificationHead.from_model_type_and_config(
                        this_model_type, model_config
                    )
                )
            else:
                this_model = get_this_model()
        else:
            this_model = get_this_model()
        this_model.resize_token_embeddings(this_vocab_size)
        return this_model
    else:
        if task == SEQREGRESSION:
            model_config_num_labels = 1
        model_config = _set_model_config(checkpoint_path)
        this_model = get_this_model()
        return this_model


def compute_checkpoint_freq(
    train_data_size,
    custom_hpo_args,
    num_train_epochs,
    batch_size,
):
    ckpt_step_freq = (
        int(
            min(num_train_epochs, 1)
            * train_data_size
            / batch_size
            / custom_hpo_args.ckpt_per_epoch
        )
        + 1
    )
    return ckpt_step_freq


@dataclass
class HPOArgs:
    """The HPO setting

    Args:
        output_dir (:obj:`str`):
            data root directory for outputing the log, etc.
        model_path (:obj:`str`, `optional`, defaults to :obj:`facebook/muppet-roberta-base`):
            A string, the path of the language model file, either a path from huggingface
            model card huggingface.co/models, or a local path for the model
        fp16 (:obj:`bool`, `optional`, defaults to :obj:`False`):
            A bool, whether to use FP16
        max_seq_length (:obj:`int`, `optional`, defaults to :obj:`128`):
            An integer, the max length of the sequence
        ckpt_per_epoch (:obj:`int`, `optional`, defaults to :obj:`1`):
            An integer, the number of checkpoints per epoch

    """

    output_dir: str = field(
        default="data/output/", metadata={"help": "data dir", "required": True}
    )

    model_path: str = field(
        default="facebook/muppet-roberta-base",
        metadata={"help": "model path model for HPO"},
    )

    fp16: bool = field(default=True, metadata={"help": "whether to use the FP16 mode"})

    max_seq_length: int = field(default=128, metadata={"help": "max seq length"})

    ckpt_per_epoch: int = field(default=1, metadata={"help": "checkpoint per epoch"})

    @staticmethod
    def load_args():
        from dataclasses import fields

        arg_parser = argparse.ArgumentParser()
        for each_field in fields(HPOArgs):
            print(each_field)
            arg_parser.add_argument(
                "--" + each_field.name,
                type=each_field.type,
                help=each_field.metadata["help"],
                required=each_field.metadata["required"]
                if "required" in each_field.metadata
                else False,
                choices=each_field.metadata["choices"]
                if "choices" in each_field.metadata
                else None,
                default=each_field.default,
            )
        console_args, unknown = arg_parser.parse_known_args()
        return console_args
