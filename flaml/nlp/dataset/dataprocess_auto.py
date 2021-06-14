from collections import OrderedDict
from functools import partial

from transformers import AutoTokenizer
from .sentence_keys_auto import get_sentence_keys


def inserting_sepp(sent, start, end, this_tokenizer):
    return \
        sent[:start].rstrip() + " " + this_tokenizer.sep_token + " " + sent[start:end] \
        + " " + this_tokenizer.sep_token + " " + sent[end:].lstrip()


def tokenize_superglue_copa(this_example,
                            this_tokenizer,
                            dataset_name,
                            subdataset_name=None,
                            **kwargs):
    return None


def tokenize_superglue_wic_gpt2(this_example,
                                this_tokenizer,
                                dataset_name,
                                subdataset_name=None,
                                **kwargs):
    return None


def tokenize_superglue_wic(this_example,
                           this_tokenizer,
                           dataset_name,
                           subdataset_name=None,
                           **kwargs
                           ):
    """
        tokenize the data from the wic task (word-in-context dataset),
        e.g., sentence 1: "There's a lot of trash on the bed of the river"
        sentence 2: "I keep a glass of water next to my bed when I sleep",
        label = False (different word senses)
        In the superglue data, the position of the word in sentence 1 and 2 are provided
        What this function does is to update the span position after tokenization, based on each LM's own tokenizer,
        The key is to insert an [SEP] before and after the original sentence, then feed it into the LM's tokenizer.
        There are two challenges:
           (1) Each LM's tokenizations are different, e.g., in XLNet's tokenizer, the paddings are on the left'
           (2) Some LM's tokenization would add an underline symbol before the word, e.g., "There's a lot"
           -> [_There, _', _s, _a, _lot]
           When underline meets special char such as '"', "'", the tokenized sequence after adding [SEP] needs to be
           aligned with the sequence tokenized without [SEP]. We use a two pointer algorithm for the alignment
    """
    sent1, sent2 = this_example["sentence1"], this_example["sentence2"]
    start1, end1 = this_example["start1"], this_example["end1"]
    start2, end2 = this_example["start2"], this_example["end2"]
    """
        Add [SEP] to the sentence
    """
    altered_sent1 = inserting_sepp(sent1, start1, end1, this_tokenizer)
    altered_sent2 = inserting_sepp(sent2, start2, end2, this_tokenizer)
    input_ids_sepp = this_tokenizer(*(altered_sent1, altered_sent2),
                                    padding="max_length",
                                    max_length=1024,
                                    truncation=True)["input_ids"]
    data_pair = (sent1, sent2)
    assert "max_seq_length" in kwargs, "max_seq_length must be provided for glue"
    this_data = this_tokenizer(*data_pair, padding="max_length", max_length=kwargs["max_seq_length"], truncation=True)
    input_ids = this_data["input_ids"]
    which_sepp = 0

    """
        span_start_end: a 2x2 array:
        * (span_start_end[0][0], span_start_end[0][1]) are the spans of the position of the word in the first sentence
        * (span_start_end[1][0], span_start_end[1][1]) are the spans of the position of the word in the second sentence
    """
    span_start_end = [[-1, -1], [-1, -1]]

    ptr_sepp = ptr_nosepp = 0
    try:
        padding_direction = this_tokenizer.padding_side
        if padding_direction == "left":
            padding_id = input_ids_sepp[0]
            while input_ids_sepp[ptr_sepp] == padding_id:
                ptr_sepp += 1
            while input_ids[ptr_nosepp] == padding_id:
                ptr_nosepp += 1
    except KeyError:
        pass
    sep_id = this_tokenizer.convert_tokens_to_ids([this_tokenizer.sep_token])[0]
    """
        use two pointers to align the tokenized sequence before and after adding [SEP];
        ptr_sepp: the pointer after adding; ptr_nosepp: the pointer without adding
    """
    while ptr_sepp < len(input_ids_sepp) and ptr_nosepp < len(input_ids) and \
            input_ids_sepp[ptr_sepp] != 0 and input_ids[ptr_nosepp] != 0:
        if input_ids_sepp[ptr_sepp] == input_ids[ptr_nosepp]:
            ptr_sepp += 1
            ptr_nosepp += 1
        else:
            if not (input_ids_sepp[ptr_sepp] == sep_id
                    or this_tokenizer.convert_ids_to_tokens([input_ids_sepp[ptr_sepp]])[0] in ('▁', '_')):
                break
            if input_ids_sepp[ptr_sepp] == sep_id:
                span_start_end[int(which_sepp / 2)][which_sepp % 2] = ptr_nosepp
                which_sepp += 1
                ptr_sepp += 1
            else:
                ptr_sepp += 1
    """
        max_word_span is the maximum tokens of the word
        It is set to 16 following deberta:
        https://github.com/microsoft/DeBERTa/blob/master/DeBERTa/apps/tasks/superglue_tasks.py#L1054
    """
    max_word_span = 16
    word_indices = []
    for idx1 in range(2):
        if span_start_end[idx1][1] < kwargs["max_seq_length"]:
            first_span = [x for x in range(span_start_end[idx1][0], span_start_end[idx1][1])
                          if x < kwargs["max_seq_length"]] + [0] * (max_word_span - span_start_end[idx1][1]
                                                                    + span_start_end[idx1][0])
            word_indices.append(first_span)
    this_data["word_spans"] = word_indices
    return this_data


def tokenize_glue(this_example,
                  this_tokenizer,
                  dataset_name,
                  subdataset_name=None,
                  **kwargs):
    sentence_keys = get_sentence_keys(dataset_name, subdataset_name)

    if len(sentence_keys) > 1:
        sentence1_key, sentence2_key = sentence_keys[0], sentence_keys[1]
    else:
        sentence1_key = sentence_keys[0]
        sentence2_key = None

    data_pair = (
        (this_example[sentence1_key],) if sentence2_key is None else (
            this_example[sentence1_key], this_example[sentence2_key])
    )
    assert "max_seq_length" in kwargs, "max_seq_length must be provided for glue"
    return this_tokenizer(*data_pair, padding="max_length", max_length=kwargs["max_seq_length"], truncation=True)


TOKENIZER_MAPPING = OrderedDict(
    [
        (("glue", "rte"), tokenize_glue),
        (("glue", "mrpc"), tokenize_glue),
        (("glue", "cola"), tokenize_glue),
        (("glue", "wnli"), tokenize_glue),
        (("glue", "stsb"), tokenize_glue),
        (("glue", "sst2"), tokenize_glue),
        (("glue", "mnli"), tokenize_glue),
        (("glue", "qqp"), tokenize_glue),
        (("glue", "qnli"), tokenize_glue),
        (("super_glue", "wic"), tokenize_superglue_wic),
    ]
)


class AutoEncodeText:
    """
    This is a generic input text tokenization class that will be instantiated as one of the
    tokenization classes of the library when created with the
    `~flaml.nlp.dataset.AutoEncodeText.from_model_and_dataset_name` class method.

    This class cannot be instantiated directly using ``__init__()`` (throws an error).
    """

    def __init__(self):
        raise EnvironmentError(
            "AutoEncodeText is designed to be instantiated "
            "using the `AutoEncodeText.from_model_and_dataset_name(cls,"
            "data_raw,model_checkpoint_path,dataset_name,subdataset_name = None,**kwargs)` methods."
        )

    @classmethod
    def from_model_and_dataset_name(cls,
                                    data_raw,
                                    model_checkpoint_path,
                                    dataset_name_list: list = None,
                                    subdataset_name=None,
                                    **kwargs):
        """
        Instantiate one of the input text tokenization classes from the raw data, model checkpoint path, dataset name
        and sub dataset name. The raw data is used for creating a mapping function from the raw tokens to the
        tokenized token ids.

        Args:
            data_raw:
                The raw data (a datasets.Dataset object)

            model_checkpoint_path:
                A string variable which specifies the model path, e.g., "google/electra-base-discriminator"

            dataset_name_list:
                A list which is the dataset name, e.g., ["glue"]

            subdataset_name:
                A string variable which is the sub dataset name,e.g., "rte"

            kwargs:
                The values in kwargs of any keys will be used for the mapping function

        Examples:
            >>> from datasets import load_dataset
            >>> data_raw = load_dataset("glue", "rte")
            >>> AutoEncodeText.from_model_and_dataset_name(data_raw, "google/electra-base-discriminator", ["glue"], "rte")

        """
        from ..result_analysis.azure_utils import JobID
        dataset_name = JobID.dataset_list_to_str(dataset_name_list)
        if (dataset_name, subdataset_name) in TOKENIZER_MAPPING.keys():
            this_tokenizer = AutoTokenizer.from_pretrained(model_checkpoint_path, use_fast=True)
            token_func = TOKENIZER_MAPPING[(dataset_name, subdataset_name)]
            return data_raw.map(
                partial(token_func,
                        this_tokenizer=this_tokenizer,
                        dataset_name=dataset_name,
                        subdataset_name=subdataset_name,
                        **kwargs), batched=False)
        raise ValueError(
            "Unrecognized method {},{} for this kind of AutoGridSearchSpace: {}.\n"
            "Method name should be one of {}.".format(
                dataset_name, subdataset_name, cls.__name__, ", ".join(c[0] for c in TOKENIZER_MAPPING.keys())
            )
        )
