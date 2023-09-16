from itertools import chain
import numpy as np
from flaml.automl.task.task import (
    SUMMARIZATION,
    SEQREGRESSION,
    SEQCLASSIFICATION,
    MULTICHOICECLASSIFICATION,
    TOKENCLASSIFICATION,
    NLG_TASKS,
)
from flaml.automl.data import pd


def todf(X, Y, column_name):
    """
    todf converts Y from any format (list, pandas.Series, numpy array) to a DataFrame before being returned
    """
    if Y is not None:
        Y = pd.DataFrame(Y, index=X.index)
        Y.columns = column_name
    return Y


def tokenize_text(X, Y=None, task=None, hf_args=None, tokenizer=None):
    label_col_name = None
    # label_col_name is the name of the label column Y, label_col_name = ['labels'] for TOKENCLASSIFICATION and SUMMARIZATION,
    # label_col_name = ['label'] for other tasks. todf is used by all tasks except for SUMMARIZATION,
    # because the outputs of tokenize_seq2seq are already two DataFrames so no conversion needed.
    if task in (SEQCLASSIFICATION, SEQREGRESSION):
        X_tokenized = tokenize_onedataframe(
            X,
            tokenizer=tokenizer,
            task=task,
            hf_args=hf_args,
            prefix_str="",
        )
        Y_tokenized = Y
        label_col_name = ["label"]
    elif task == TOKENCLASSIFICATION:
        X_tokenized, Y_tokenized = tokenize_text_tokclassification(X, Y, tokenizer=tokenizer, hf_args=hf_args)
        label_col_name = ["labels"]
    elif task in NLG_TASKS:
        return tokenize_seq2seq(X, Y, tokenizer=tokenizer, task=task, hf_args=hf_args)
    elif task == MULTICHOICECLASSIFICATION:
        X_tokenized = tokenize_text_multiplechoice(X, tokenizer=tokenizer, hf_args=hf_args)
        label_col_name = ["label"]
        Y_tokenized = Y
    Y_tokenized = todf(X_tokenized, Y_tokenized, label_col_name)
    return X_tokenized, Y_tokenized


def tokenize_seq2seq(X, Y, tokenizer, task=None, hf_args=None):
    model_inputs = tokenize_onedataframe(
        X,
        tokenizer=tokenizer,
        task=task,
        hf_args=hf_args,
        prefix_str="summarize: ",
    )
    model_outputs = None
    if Y is not None:
        model_outputs = tokenize_onedataframe(
            Y.to_frame(),
            tokenizer=tokenizer,
            task=task,
            hf_args=hf_args,
            prefix_str="",
        )
        model_outputs["labels"] = [
            [(each_l if each_l != tokenizer.pad_token_id else -100) for each_l in label]
            for label in model_outputs["input_ids"]
        ]
        model_outputs = model_outputs.drop(columns=["attention_mask", "input_ids", "decoder_input_ids"])
    return model_inputs, model_outputs


def tokenize_and_align_labels(
    examples,
    tokenizer,
    label_to_id,
    b_to_i_label,
    hf_args=None,
    X_sent_key=None,
    Y_sent_key=None,
    return_column_name=False,
):
    # tokenize_and_align_labels is only called by the token-classification task
    tokenized_inputs = tokenizer(
        [list(examples[X_sent_key])],
        padding="max_length"
        if hf_args and hf_args.pad_to_max_length
        else False,  # to be consistent with https://github.com/huggingface/transformers/blob/main/examples/pytorch/token-classification/run_ner.py#L394
        truncation=True,
        max_length=hf_args.max_seq_length if hf_args else None,
        # We use this argument because the texts in our dataset are lists of words (with a label for each word).
        is_split_into_words=True,
    )
    if Y_sent_key is not None:
        previous_word_idx = None
        label_ids = []
        for word_idx in tokenized_inputs.word_ids(batch_index=0):
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:
                label_ids.append(label_to_id[examples[Y_sent_key][word_idx]])
            # For the other tokens in a word, we set the label to either the current label or -100, depending on
            # the label_all_tokens flag.
            else:
                # Use the label_all_tokens to control whether to copy the label to all subtokens or to pad the additional tokens as -100
                if hf_args.label_all_tokens:
                    # If the B- word is converted into multiple subtokens, map the additional subtokens to I-
                    label_ids.append(b_to_i_label[label_to_id[examples[Y_sent_key][word_idx]]])
                else:
                    label_ids.append(-100)
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
    # If the label_all_tokens flag is True, prepare two dicts label_to_id and b_to_i_label to convert the B- labels to I- labels
    label_to_id = {i: i for i in range(len(hf_args.label_list))}
    b_to_i_label = []
    for idx, label in enumerate(hf_args.label_list):
        if label.startswith("B-") and label.replace("B-", "I-") in hf_args.label_list:
            b_to_i_label.append(hf_args.label_list.index(label.replace("B-", "I-")))
        else:
            b_to_i_label.append(idx)

    if Y is not None:
        X_and_Y = pd.concat([X, Y.to_frame()], axis=1)
        X_key = list(X.keys())[0]
        Y_key = list(Y.to_frame().keys())[0]
        # tokenize_and_align_labels is only called by the token-classification task
        _, tokenized_column_names = tokenize_and_align_labels(
            X_and_Y.iloc[0],
            tokenizer=tokenizer,
            hf_args=hf_args,
            X_sent_key=X_key,
            Y_sent_key=Y_key,
            return_column_name=True,
            label_to_id=label_to_id,
            b_to_i_label=b_to_i_label,
        )
        X_and_Y_tokenized = X_and_Y.apply(
            lambda x: tokenize_and_align_labels(
                x,
                tokenizer=tokenizer,
                hf_args=hf_args,
                X_sent_key=X_key,
                Y_sent_key=Y_key,
                label_to_id=label_to_id,
                b_to_i_label=b_to_i_label,
            ),
            axis=1,
            result_type="expand",
        )
        label_idx = tokenized_column_names.index("labels")
        other_indices = sorted(set(range(len(tokenized_column_names))).difference({label_idx}))
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
            label_to_id=label_to_id,
            b_to_i_label=b_to_i_label,
        )

        d = X.apply(
            lambda x: tokenize_and_align_labels(
                x,
                tokenizer=tokenizer,
                hf_args=hf_args,
                X_sent_key=X_key,
                Y_sent_key=None,
                label_to_id=label_to_id,
                b_to_i_label=b_to_i_label,
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
        X_tokenized = pd.DataFrame(columns=tokenized_column_names)
        X_tokenized[tokenized_column_names] = d
        return X_tokenized


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
        padding="max_length" if hf_args and hf_args.pad_to_max_length else False,
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

    X_tokenized = pd.DataFrame(columns=tokenized_column_names)
    X_tokenized[tokenized_column_names] = d
    output = X_tokenized.join(X)
    return output


def tokenize_swag(this_row, tokenizer, hf_args=None, return_column_name=False):
    first_sentences = [[this_row["sent1"]] * 4]
    # get each 1st sentence, multiply to 4 sentences
    question_headers = this_row["sent2"]
    # sent2 are the noun part of 2nd line
    second_sentences = [question_headers + " " + this_row[key] for key in ["ending0", "ending1", "ending2", "ending3"]]
    # now the 2nd-sentences are formed by combing the noun part and 4 ending parts

    # Flatten out
    # From 2 dimension to 1 dimension array
    first_sentences = list(chain(*first_sentences))

    tokenized_example = tokenizer(
        *tuple([first_sentences, second_sentences]),
        truncation=True,
        max_length=hf_args.max_seq_length if hf_args else None,
        padding="max_length" if hf_args and hf_args.pad_to_max_length else False,
    )
    tmp_column_names = sorted(tokenized_example.keys())

    if return_column_name:
        return [tokenized_example[x] for x in tmp_column_names], tmp_column_names
    else:
        return [tokenized_example[x] for x in tmp_column_names]


def postprocess_prediction_and_true(task, y_pred, tokenizer, hf_args, y_true=None, X=None):
    # postprocess the matrix prediction y_pred and ground truth y_true into user readable format, e.g., for summarization, decode into text
    if y_pred is None:
        return np.array([0.0] * len(X)), y_true
    if task == SEQCLASSIFICATION:
        return np.argmax(y_pred, axis=1), y_true
    elif task == SEQREGRESSION:
        return np.squeeze(y_pred), y_true  # predictions.reshape((len(predictions),))
    elif task == TOKENCLASSIFICATION:
        assert (y_true is not None) or (X is not None), "One of y_true and X must not be None"
        ## If y_true is not None, we use y_true to remove the -100 in the prediction (postprocessing), and return the postprocessed y_true and prediction
        # If y_true is None, we use X to compute y_is_pad (i.e., whether y_true is -100 in that position), and use y_is_pad to remove the -100 in the prediction, and return the postprocessed prediction (not the y_true)
        y_predict = pd.Series(np.argmax(y_pred, axis=2).tolist())
        if y_true is None:
            _, y_is_pad_df = tokenize_text(
                X,
                y_predict,
                task=task,
                hf_args=hf_args,
                tokenizer=tokenizer,
            )
            y_is_pad = y_is_pad_df.iloc[:, 0]
        else:
            y_is_pad = y_true
        label_len = len(hf_args.label_list)
        zip_pred_ispad = [
            [(p, ispd) for (p, ispd) in zip(each_pred, each_is_pad) if ispd != -100]
            for (each_pred, each_is_pad) in zip(y_predict, y_is_pad)
        ]
        y_pred_label = [
            [hf_args.label_list[p] if 0 <= p < label_len else -1 for (p, ispd) in each_list]
            for each_list in zip_pred_ispad
        ]  # To compute precision and recall, y_pred and y_true must be converted to string labels
        # (B-PER, I-PER, etc.), so that the category-based precision/recall (i.e., PER, LOC, etc.) scores can be computed
        if y_true is not None:
            y_true_label = [[tr for (p, tr) in each_list] for each_list in zip_pred_ispad]
        else:
            y_true_label = None
        return y_pred_label, y_true_label
    elif task == SUMMARIZATION:
        if isinstance(y_pred, tuple):
            y_pred = np.argmax(y_pred[0], axis=2)
        decoded_preds = tokenizer.batch_decode(y_pred, skip_special_tokens=True)

        import nltk

        nltk.download("punkt")
        decoded_preds = [pred.strip() for pred in decoded_preds]
        decoded_preds = ["\n".join(nltk.sent_tokenize(pred)) for pred in decoded_preds]

        if y_true is not None:
            y_true_labels = np.where(y_true != -100, y_true, tokenizer.pad_token_id)
            decoded_y_true_labels = tokenizer.batch_decode(y_true_labels, skip_special_tokens=True)
            decoded_y_true_labels = [label.strip() for label in decoded_y_true_labels]
            decoded_y_true_labels = ["\n".join(nltk.sent_tokenize(label)) for label in decoded_y_true_labels]
        else:
            decoded_y_true_labels = None

        return decoded_preds, decoded_y_true_labels
    elif task == MULTICHOICECLASSIFICATION:
        return np.argmax(y_pred, axis=1), y_true


def load_model(checkpoint_path, task, num_labels=None):
    import transformers

    transformers.logging.set_verbosity_error()

    from transformers import AutoConfig
    from flaml.automl.task.task import (
        SEQCLASSIFICATION,
        SEQREGRESSION,
        TOKENCLASSIFICATION,
    )

    def get_this_model(checkpoint_path, task, model_config):
        from transformers import AutoModelForSequenceClassification
        from transformers import AutoModelForSeq2SeqLM
        from transformers import AutoModelForMultipleChoice
        from transformers import AutoModelForTokenClassification

        if task in (SEQCLASSIFICATION, SEQREGRESSION):
            return AutoModelForSequenceClassification.from_pretrained(
                checkpoint_path, config=model_config, ignore_mismatched_sizes=True
            )
        elif task == TOKENCLASSIFICATION:
            return AutoModelForTokenClassification.from_pretrained(checkpoint_path, config=model_config)
        elif task in NLG_TASKS:
            return AutoModelForSeq2SeqLM.from_pretrained(checkpoint_path, config=model_config)
        elif task == MULTICHOICECLASSIFICATION:
            return AutoModelForMultipleChoice.from_pretrained(checkpoint_path, config=model_config)

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
    this_vocab_size = current_config.vocab_size

    model_config_num_labels = num_labels
    new_config = _set_model_config(checkpoint_path)

    this_model = get_this_model(checkpoint_path, task, new_config)
    this_model.resize_token_embeddings(this_vocab_size)
    return this_model
