import argparse
from dataclasses import dataclass, field
from itertools import chain
from typing import Dict, Any

from ..data import (
    SUMMARIZATION,
    SEQREGRESSION,
    SEQCLASSIFICATION,
    MULTICHOICECLASSIFICATION,
    TOKENCLASSIFICATION,
    NLG_TASKS,
)


def load_default_huggingface_metric_for_task(task):

    if task == SEQCLASSIFICATION:
        return "accuracy"
    elif task == SEQREGRESSION:
        return "r2"
    elif task == SUMMARIZATION:
        return "rouge"
    elif task == MULTICHOICECLASSIFICATION:
        return "accuracy"
    elif task == TOKENCLASSIFICATION:
        return "seqeval"


global tokenized_column_names


def get_auto_tokenizer(model_path, task):
    from transformers import AutoTokenizer

    if task == SUMMARIZATION:
        return AutoTokenizer.from_pretrained(
            model_path,  # 'roberta-base'
            cache_dir=None,
            use_fast=True,
            revision="main",
            use_auth_token=None,
        )
    else:
        return AutoTokenizer.from_pretrained(model_path, use_fast=True)


def tokenize_text(X, Y=None, task=None, custom_hpo_args=None, tokenizer=None):
    if task in (SEQCLASSIFICATION, SEQREGRESSION):
        X_tokenized = tokenize_onedataframe(
            X,
            tokenizer=tokenizer,
            task=task,
            custom_hpo_args=custom_hpo_args,
            prefix_str="",
        )
        return X_tokenized, None
    elif task == TOKENCLASSIFICATION:
        return tokenize_text_tokclassification(
            X, Y, tokenizer=tokenizer, custom_hpo_args=custom_hpo_args
        )
    elif task in NLG_TASKS:
        return tokenize_seq2seq(
            X, Y, tokenizer=tokenizer, task=task, custom_hpo_args=custom_hpo_args
        )
    elif task == MULTICHOICECLASSIFICATION:
        return tokenize_text_multiplechoice(
            X, tokenizer=tokenizer, custom_hpo_args=custom_hpo_args
        )


def tokenize_seq2seq(X, Y, tokenizer, task=None, custom_hpo_args=None):
    model_inputs = tokenize_onedataframe(
        X,
        tokenizer=tokenizer,
        task=task,
        custom_hpo_args=custom_hpo_args,
        prefix_str="summarize: ",
    )
    labels = None
    if Y is not None:
        labels = tokenize_onedataframe(
            Y.to_frame(),
            tokenizer=tokenizer,
            task=task,
            custom_hpo_args=custom_hpo_args,
            prefix_str="",
        )
        labels["label"] = [
            [(each_l if each_l != tokenizer.pad_token_id else -100) for each_l in label]
            for label in labels["input_ids"]
        ]
        labels = labels.drop(
            columns=["attention_mask", "input_ids", "decoder_input_ids"]
        )
    return model_inputs, labels


def tokenize_and_align_labels(
    examples, tokenizer, custom_hpo_args=None, X_sent_key=None, Y_sent_key=None
):
    global tokenized_column_names

    tokenized_inputs = tokenizer(
        [list(examples[X_sent_key])],
        padding="max_length",
        truncation=True,
        max_length=custom_hpo_args.max_seq_length,
        # We use this argument because the texts in our dataset are lists of words (with a label for each word).
        is_split_into_words=True,
    )
    if Y_sent_key is not None:
        previous_word_idx = None
        label_ids = []
        import numbers

        for word_idx in tokenized_inputs.word_ids(batch_index=0):
            # Special tokens have a word id that is None. We set the label to -100 so they are automatically
            # ignored in the loss function.
            if word_idx is None:
                label_ids.append(-100)
            # We set the label for the first token of each word.
            elif word_idx != previous_word_idx:
                if isinstance(examples[Y_sent_key][word_idx], numbers.Number):
                    label_ids.append(examples[Y_sent_key][word_idx])
                # else:
                #     label_ids.append(label_to_id[label[word_idx]])
            # For the other tokens in a word, we set the label to either the current label or -100, depending on
            # the label_all_tokens flag.
            else:
                if isinstance(examples[Y_sent_key][word_idx], numbers.Number):
                    label_ids.append(examples[Y_sent_key][word_idx])
                # else:
                #     label_ids.append(b_to_i_label[label_to_id[label[word_idx]]])
            previous_word_idx = word_idx
        tokenized_inputs["label"] = label_ids
    tokenized_column_names = sorted(tokenized_inputs.keys())
    tokenized_input_and_labels = [tokenized_inputs[x] for x in tokenized_column_names]
    for key_idx, each_key in enumerate(tokenized_column_names):
        if each_key != "label":
            tokenized_input_and_labels[key_idx] = tokenized_input_and_labels[key_idx][0]
    return tokenized_input_and_labels


def tokenize_text_tokclassification(X, Y, tokenizer, custom_hpo_args=None):
    import pandas as pd

    global tokenized_column_names
    if Y is not None:
        X_and_Y = pd.concat([X, Y.to_frame()], axis=1)
        X_key = list(X.keys())[0]
        Y_key = list(Y.to_frame().keys())[0]
        X_and_Y_tokenized = X_and_Y.apply(
            lambda x: tokenize_and_align_labels(
                x,
                tokenizer=tokenizer,
                custom_hpo_args=custom_hpo_args,
                X_sent_key=X_key,
                Y_sent_key=Y_key,
            ),
            axis=1,
            result_type="expand",
        )
        label_idx = tokenized_column_names.index("label")
        other_indices = sorted(
            set(range(len(tokenized_column_names))).difference({label_idx})
        )
        other_column_names = [tokenized_column_names[x] for x in other_indices]
        d = X_and_Y_tokenized.iloc[:, other_indices]
        y_tokenized = X_and_Y_tokenized.iloc[:, label_idx]
    else:
        X_key = list(X.keys())[0]
        d = X.apply(
            lambda x: tokenize_and_align_labels(
                x,
                tokenizer=tokenizer,
                custom_hpo_args=custom_hpo_args,
                X_sent_key=X_key,
                Y_sent_key=None,
            ),
            axis=1,
            result_type="expand",
        )
        other_column_names = tokenized_column_names
        y_tokenized = None
    X_tokenized = pd.DataFrame(columns=other_column_names)
    X_tokenized[other_column_names] = d
    return X_tokenized, y_tokenized


def tokenize_onedataframe(
    X,
    tokenizer,
    task=None,
    custom_hpo_args=None,
    prefix_str=None,
):
    import pandas

    global tokenized_column_names

    with tokenizer.as_target_tokenizer():
        d = X.apply(
            lambda x: tokenize_row(
                x,
                tokenizer,
                prefix=(prefix_str,) if task is SUMMARIZATION else None,
                task=task,
                custom_hpo_args=custom_hpo_args,
            ),
            axis=1,
            result_type="expand",
        )
    X_tokenized = pandas.DataFrame(columns=tokenized_column_names)
    X_tokenized[tokenized_column_names] = d
    return X_tokenized


def postprocess_text(preds, labels):
    import nltk

    nltk.download("punkt")
    preds = [pred.strip() for pred in preds]
    labels = [label.strip() for label in labels]

    # rougeLSum expects newline after each sentence
    preds = ["\n".join(nltk.sent_tokenize(pred)) for pred in preds]
    labels = ["\n".join(nltk.sent_tokenize(label)) for label in labels]

    return preds, labels


def tokenize_row(this_row, tokenizer, prefix=None, task=None, custom_hpo_args=None):
    global tokenized_column_names
    assert (
        "max_seq_length" in custom_hpo_args.__dict__
    ), "max_seq_length must be provided for glue"

    if prefix:
        this_row = tuple(["".join(x) for x in zip(prefix, this_row)])

    tokenized_example = tokenizer(
        *tuple(this_row),
        padding="max_length",
        max_length=custom_hpo_args.max_seq_length,
        truncation=True,
    )
    if task in NLG_TASKS:
        tokenized_example["decoder_input_ids"] = tokenized_example["input_ids"]
    tokenized_column_names = sorted(tokenized_example.keys())
    return [tokenized_example[x] for x in tokenized_column_names]


def tokenize_text_multiplechoice(X, tokenizer, custom_hpo_args=None):
    import pandas

    global tokenized_column_names

    t = X[["sent1", "sent2", "ending0", "ending1", "ending2", "ending3"]]
    d = t.apply(
        lambda x: tokenize_swag(x, tokenizer, custom_hpo_args),
        axis=1,
        result_type="expand",
    )

    X_tokenized = pandas.DataFrame(columns=tokenized_column_names)
    X_tokenized[tokenized_column_names] = d
    output = X_tokenized.join(X)
    return output, None


def tokenize_swag(this_row, tokenizer, custom_hpo_args=None):
    global tokenized_column_names

    first_sentences = [[this_row["sent1"]] * 4]
    # get each 1st sentence, multiply to 4 sentences
    question_headers = this_row["sent2"]
    # sent2 are the noun part of 2nd line
    second_sentences = [
        question_headers + " " + this_row[key]
        for key in ["ending0", "ending1", "ending2", "ending3"]
    ]
    # now the 2nd-sentences are formed by combing the noun part and 4 ending parts

    # Flatten out
    # From 2 dimension to 1 dimension array
    first_sentences = list(chain(*first_sentences))

    tokenized_example = tokenizer(
        *tuple([first_sentences, second_sentences]),
        truncation=True,
        max_length=custom_hpo_args.max_seq_length,
        padding=False,
    )
    tokenized_column_names = sorted(tokenized_example.keys())
    return [tokenized_example[x] for x in tokenized_column_names]


def separate_config(config, task):
    if task in NLG_TASKS:
        from transformers import Seq2SeqTrainingArguments, TrainingArguments

        trainargs_class_list = [Seq2SeqTrainingArguments, TrainingArguments]
    else:
        from transformers import TrainingArguments

        trainargs_class_list = [TrainingArguments]

    training_args_config = {}
    per_model_config = {}

    for key, val in config.items():
        is_in_training_args = any(key in x.__dict__ for x in trainargs_class_list)
        if is_in_training_args:
            training_args_config[key] = val
        else:
            per_model_config[key] = val

    return training_args_config, per_model_config


def get_num_labels(task, y_train):
    from ..data import SEQCLASSIFICATION, SEQREGRESSION, TOKENCLASSIFICATION

    if task == SEQREGRESSION:
        return 1
    elif task == SEQCLASSIFICATION:
        return len(set(y_train))
    elif task == TOKENCLASSIFICATION:
        return len(set([a for b in y_train.tolist() for a in b]))
    else:
        return None


def is_a_list_of_str(this_obj):
    return isinstance(this_obj, list) and all(isinstance(x, str) for x in this_obj)


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
    import transformers

    transformers.logging.set_verbosity_error()

    from transformers import AutoConfig
    from .huggingface.switch_head_auto import (
        AutoSeqClassificationHead,
        MODEL_CLASSIFICATION_HEAD_MAPPING,
    )
    from ..data import SEQCLASSIFICATION, SEQREGRESSION, TOKENCLASSIFICATION

    this_model_type = AutoConfig.from_pretrained(checkpoint_path).model_type
    this_vocab_size = AutoConfig.from_pretrained(checkpoint_path).vocab_size

    def get_this_model(task):
        from transformers import AutoModelForSequenceClassification
        from transformers import AutoModelForSeq2SeqLM
        from transformers import AutoModelForMultipleChoice
        from transformers import AutoModelForTokenClassification

        if task in (SEQCLASSIFICATION, SEQREGRESSION):
            return AutoModelForSequenceClassification.from_pretrained(
                checkpoint_path, config=model_config
            )
        elif task == TOKENCLASSIFICATION:
            return AutoModelForTokenClassification.from_pretrained(
                checkpoint_path, config=model_config
            )
        elif task in NLG_TASKS:
            return AutoModelForSeq2SeqLM.from_pretrained(
                checkpoint_path, config=model_config
            )
        elif task == MULTICHOICECLASSIFICATION:
            return AutoModelForMultipleChoice.from_pretrained(
                checkpoint_path, config=model_config
            )

    def is_pretrained_model_in_classification_head_list(model_type):
        return model_type in MODEL_CLASSIFICATION_HEAD_MAPPING

    def _set_model_config(checkpoint_path):
        if task in (SEQCLASSIFICATION, SEQREGRESSION, TOKENCLASSIFICATION):
            if per_model_config:
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
        else:
            if per_model_config:
                model_config = AutoConfig.from_pretrained(
                    checkpoint_path,
                    **per_model_config,
                )
            else:
                model_config = AutoConfig.from_pretrained(checkpoint_path)
            return model_config

    if task == SEQCLASSIFICATION:
        num_labels_old = AutoConfig.from_pretrained(checkpoint_path).num_labels
        if is_pretrained_model_in_classification_head_list(this_model_type):
            model_config_num_labels = num_labels_old
        else:
            model_config_num_labels = num_labels
        model_config = _set_model_config(checkpoint_path)

        if is_pretrained_model_in_classification_head_list(this_model_type):
            if num_labels != num_labels_old:
                this_model = get_this_model(task)
                model_config.num_labels = num_labels
                this_model.num_labels = num_labels
                this_model.classifier = (
                    AutoSeqClassificationHead.from_model_type_and_config(
                        this_model_type, model_config
                    )
                )
            else:
                this_model = get_this_model(task)
        else:
            this_model = get_this_model(task)
        this_model.resize_token_embeddings(this_vocab_size)
        return this_model
    else:
        if task == SEQREGRESSION:
            model_config_num_labels = 1
        elif task == TOKENCLASSIFICATION:
            model_config_num_labels = num_labels
        model_config = _set_model_config(checkpoint_path)
        this_model = get_this_model(task)
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
    """The HPO setting.
    Args:
        output_dir (str): data root directory for outputing the log, etc.
        model_path (str, optional, defaults to "facebook/muppet-roberta-base"): A string,
            the path of the language model file, either a path from huggingface
            model card huggingface.co/models, or a local path for the model.
        fp16 (bool, optional, defaults to "False"): A bool, whether to use FP16.
        max_seq_length (int, optional, defaults to 128): An integer, the max length of the sequence.
        ckpt_per_epoch (int, optional, defaults to 1): An integer, the number of checkpoints per epoch.
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

    pad_to_max_length: bool = field(
        default=True,
        metadata={
            "help": "Whether to pad all samples to model maximum sentence length. "
            "If False, will pad the samples dynamically when batching to the maximum length in the batch. More "
            "efficient on GPU but very bad for TPU."
        },
    )

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
