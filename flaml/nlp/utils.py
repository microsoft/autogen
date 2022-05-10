from itertools import chain
from typing import Dict, Any
import numpy as np

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
        return "rouge1"
    elif task == MULTICHOICECLASSIFICATION:
        return "accuracy"
    elif task == TOKENCLASSIFICATION:
        return "seqeval"


def tokenize_text(X, Y=None, task=None, hf_args=None, tokenizer=None):
    if task in (SEQCLASSIFICATION, SEQREGRESSION):
        X_tokenized = tokenize_onedataframe(
            X,
            tokenizer=tokenizer,
            task=task,
            hf_args=hf_args,
            prefix_str="",
        )
        return X_tokenized, None
    elif task == TOKENCLASSIFICATION:
        return tokenize_text_tokclassification(
            X, Y, tokenizer=tokenizer, hf_args=hf_args
        )
    elif task in NLG_TASKS:
        return tokenize_seq2seq(X, Y, tokenizer=tokenizer, task=task, hf_args=hf_args)
    elif task == MULTICHOICECLASSIFICATION:
        return tokenize_text_multiplechoice(X, tokenizer=tokenizer, hf_args=hf_args)


def tokenize_seq2seq(X, Y, tokenizer, task=None, hf_args=None):
    model_inputs = tokenize_onedataframe(
        X,
        tokenizer=tokenizer,
        task=task,
        hf_args=hf_args,
        prefix_str="summarize: ",
    )
    labels = None
    if Y is not None:
        labels = tokenize_onedataframe(
            Y.to_frame(),
            tokenizer=tokenizer,
            task=task,
            hf_args=hf_args,
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
    examples,
    tokenizer,
    hf_args=None,
    X_sent_key=None,
    Y_sent_key=None,
    return_column_name=False,
):
    tokenized_inputs = tokenizer(
        [list(examples[X_sent_key])],
        padding="max_length"
        if hf_args.pad_to_max_length
        else False,  # to be consistent with https://github.com/huggingface/transformers/blob/main/examples/pytorch/token-classification/run_ner.py#L394
        truncation=True,
        max_length=hf_args.max_seq_length,
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
        tokenized_inputs["labels"] = label_ids
    tmp_column_names = sorted(tokenized_inputs.keys())
    tokenized_input_and_labels = [tokenized_inputs[x] for x in tmp_column_names]
    for key_idx, each_key in enumerate(tmp_column_names):
        if each_key != "labels":
            tokenized_input_and_labels[key_idx] = tokenized_input_and_labels[key_idx][0]
    if return_column_name:
        return tokenized_input_and_labels, tmp_column_names
    else:
        return tokenized_input_and_labels


def tokenize_text_tokclassification(X, Y, tokenizer, hf_args=None):
    import pandas as pd

    if Y is not None:
        X_and_Y = pd.concat([X, Y.to_frame()], axis=1)
        X_key = list(X.keys())[0]
        Y_key = list(Y.to_frame().keys())[0]
        _, tokenized_column_names = tokenize_and_align_labels(
            X_and_Y.iloc[0],
            tokenizer=tokenizer,
            hf_args=hf_args,
            X_sent_key=X_key,
            Y_sent_key=Y_key,
            return_column_name=True,
        )
        X_and_Y_tokenized = X_and_Y.apply(
            lambda x: tokenize_and_align_labels(
                x,
                tokenizer=tokenizer,
                hf_args=hf_args,
                X_sent_key=X_key,
                Y_sent_key=Y_key,
            ),
            axis=1,
            result_type="expand",
        )
        label_idx = tokenized_column_names.index("labels")
        other_indices = sorted(
            set(range(len(tokenized_column_names))).difference({label_idx})
        )
        other_column_names = [tokenized_column_names[x] for x in other_indices]
        d = X_and_Y_tokenized.iloc[:, other_indices]
        y_tokenized = X_and_Y_tokenized.iloc[:, label_idx]
    else:
        X_key = list(X.keys())[0]

        _, tokenized_column_names = tokenize_and_align_labels(
            X.iloc[0],
            tokenizer=tokenizer,
            hf_args=hf_args,
            X_sent_key=X_key,
            Y_sent_key=None,
            return_column_name=True,
        )

        d = X.apply(
            lambda x: tokenize_and_align_labels(
                x,
                tokenizer=tokenizer,
                hf_args=hf_args,
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
    hf_args=None,
    prefix_str=None,
):
    import pandas

    with tokenizer.as_target_tokenizer():
        _, tokenized_column_names = tokenize_row(
            dict(X.iloc[0]),
            tokenizer,
            prefix=(prefix_str,) if task is SUMMARIZATION else None,
            task=task,
            hf_args=hf_args,
            return_column_name=True,
        )
        d = X.apply(
            lambda x: tokenize_row(
                x,
                tokenizer,
                prefix=(prefix_str,) if task is SUMMARIZATION else None,
                task=task,
                hf_args=hf_args,
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


def tokenize_row(
    this_row,
    tokenizer,
    prefix=None,
    task=None,
    hf_args=None,
    return_column_name=False,
):
    if prefix:
        this_row = tuple(["".join(x) for x in zip(prefix, this_row)])

    # tokenizer.pad_token = tokenizer.eos_token
    tokenized_example = tokenizer(
        *tuple(this_row),
        padding="max_length",
        max_length=hf_args.max_seq_length if hf_args else None,
        truncation=True,
    )
    if task in NLG_TASKS:
        tokenized_example["decoder_input_ids"] = tokenized_example["input_ids"]
    tmp_column_names = sorted(tokenized_example.keys())

    if return_column_name:
        return [tokenized_example[x] for x in tmp_column_names], tmp_column_names
    else:
        return [tokenized_example[x] for x in tmp_column_names]


def tokenize_text_multiplechoice(X, tokenizer, hf_args=None):
    import pandas

    t = X[["sent1", "sent2", "ending0", "ending1", "ending2", "ending3"]]
    _, tokenized_column_names = tokenize_swag(
        t.iloc[0],
        tokenizer=tokenizer,
        hf_args=hf_args,
        return_column_name=True,
    )
    d = t.apply(
        lambda x: tokenize_swag(x, tokenizer=tokenizer, hf_args=hf_args),
        axis=1,
        result_type="expand",
    )

    X_tokenized = pandas.DataFrame(columns=tokenized_column_names)
    X_tokenized[tokenized_column_names] = d
    output = X_tokenized.join(X)
    return output, None


def tokenize_swag(this_row, tokenizer, hf_args=None, return_column_name=False):
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
        max_length=hf_args.max_seq_length if hf_args else None,
        padding=False,
    )
    tmp_column_names = sorted(tokenized_example.keys())

    if return_column_name:
        return [tokenized_example[x] for x in tmp_column_names], tmp_column_names
    else:
        return [tokenized_example[x] for x in tmp_column_names]


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
        experiment_tag = "{0}_{1}".format(
            str(Counter.counter), format_vars(trial_config)
        )
        logdir = get_logdir_name(
            _generate_dirname(experiment_tag, trial_id=trial_id), local_dir
        )
        return logdir


def load_model(checkpoint_path, task, num_labels=None):
    import transformers

    transformers.logging.set_verbosity_error()

    from transformers import AutoConfig
    from .huggingface.switch_head_auto import (
        AutoSeqClassificationHead,
        MODEL_CLASSIFICATION_HEAD_MAPPING,
    )
    from ..data import SEQCLASSIFICATION, SEQREGRESSION, TOKENCLASSIFICATION

    def get_this_model(checkpoint_path, task, model_config):
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
            model_config = AutoConfig.from_pretrained(
                checkpoint_path,
                num_labels=model_config_num_labels,
            )
            return model_config
        else:
            model_config = AutoConfig.from_pretrained(checkpoint_path)
            return model_config

    current_config = AutoConfig.from_pretrained(checkpoint_path)
    this_model_type, this_vocab_size = (
        current_config.model_type,
        current_config.vocab_size,
    )

    if task == SEQCLASSIFICATION:
        num_labels_old = current_config.num_labels
        if is_pretrained_model_in_classification_head_list(this_model_type):
            model_config_num_labels = num_labels_old
        else:
            model_config_num_labels = num_labels
        new_config = _set_model_config(checkpoint_path)

        if is_pretrained_model_in_classification_head_list(this_model_type):
            if num_labels != num_labels_old:
                this_model = get_this_model(checkpoint_path, task, new_config)
                new_config.num_labels = num_labels
                this_model.num_labels = num_labels
                this_model.classifier = (
                    AutoSeqClassificationHead.from_model_type_and_config(
                        this_model_type, new_config
                    )
                )
            else:
                this_model = get_this_model(checkpoint_path, task, new_config)
        else:
            this_model = get_this_model(checkpoint_path, task, new_config)
        this_model.resize_token_embeddings(this_vocab_size)
        return this_model
    else:
        if task == SEQREGRESSION:
            model_config_num_labels = 1
        elif task == TOKENCLASSIFICATION:
            model_config_num_labels = num_labels
        model_config = _set_model_config(checkpoint_path)
        this_model = get_this_model(checkpoint_path, task, model_config)
        return this_model
