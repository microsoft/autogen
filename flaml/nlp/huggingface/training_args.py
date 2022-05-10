import argparse
from dataclasses import dataclass, field

from ...data import (
    NLG_TASKS,
)
from typing import Optional, List

try:
    from transformers import TrainingArguments
except ImportError:
    TrainingArguments = object


@dataclass
class TrainingArgumentsForAuto(TrainingArguments):
    """FLAML custom TrainingArguments.

    Args:
        task (str): the task name for NLP tasks, e.g., seq-classification, token-classification
        output_dir (str): data root directory for outputing the log, etc.
        model_path (str, optional, defaults to "facebook/muppet-roberta-base"): A string,
            the path of the language model file, either a path from huggingface
            model card huggingface.co/models, or a local path for the model.
        fp16 (bool, optional, defaults to "False"): A bool, whether to use FP16.
        max_seq_length (int, optional, defaults to 128): An integer, the max length of the sequence.
        pad_to_max_length (bool, optional, defaults to "False"):
            whether to pad all samples to model maximum sentence length.
            If False, will pad the samples dynamically when batching to the maximum length in the batch.
        ckpt_per_epoch (int, optional, defaults to 1): An integer, the number of checkpoints per epoch.
        per_device_eval_batch_size (int, optional, defaults to 1): An integer, the per gpu evaluation batch size.
        label_list (List[str], optional, defaults to None): A list of string, the string list of the label names.
            When the task is sequence labeling/token classification, need to set the label_list (e.g., B-PER, I-PER, B-LOC)
            to obtain the correct evaluation metric. See the example in test/nlp/test_autohf_tokenclassification.py.
    """

    task: str = field(default="seq-classification")

    output_dir: str = field(default="data/output/", metadata={"help": "data dir"})

    model_path: str = field(
        default="facebook/muppet-roberta-base",
        metadata={
            "help": "model path for HPO natural language understanding tasks, default is set to facebook/muppet-roberta-base"
        },
    )

    fp16: bool = field(default=True, metadata={"help": "whether to use the FP16 mode"})

    max_seq_length: int = field(default=128, metadata={"help": "max seq length"})

    pad_to_max_length: bool = field(
        default=False,
        metadata={
            "help": "Whether to pad all samples to model maximum sentence length. "
            "If False, will pad the samples dynamically when batching to the maximum length in the batch. "
        },
    )

    ckpt_per_epoch: int = field(default=1, metadata={"help": "checkpoint per epoch"})

    per_device_eval_batch_size: int = field(
        default=1,
        metadata={"help": "per gpu evaluation batch size"},
    )

    label_list: Optional[List[str]] = field(
        default=None, metadata={"help": "The string list of the label names. "}
    )

    @staticmethod
    def load_args_from_console():
        from dataclasses import fields

        arg_parser = argparse.ArgumentParser()
        for each_field in fields(TrainingArgumentsForAuto):
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


@dataclass
class Seq2SeqTrainingArgumentsForAuto(TrainingArgumentsForAuto):

    model_path: str = field(
        default="t5-small",
        metadata={
            "help": "model path for HPO natural language generation tasks, default is set to t5-small"
        },
    )

    sortish_sampler: bool = field(
        default=False, metadata={"help": "Whether to use SortishSampler or not."}
    )
    predict_with_generate: bool = field(
        default=True,
        metadata={
            "help": "Whether to use generate to calculate generative metrics (ROUGE, BLEU)."
        },
    )
    generation_max_length: Optional[int] = field(
        default=None,
        metadata={
            "help": "The `max_length` to use on each evaluation loop when `predict_with_generate=True`. Will default "
            "to the `max_length` value of the model configuration."
        },
    )
    generation_num_beams: Optional[int] = field(
        default=None,
        metadata={
            "help": "The `num_beams` to use on each evaluation loop when `predict_with_generate=True`. Will default "
            "to the `num_beams` value of the model configuration."
        },
    )

    def __post_init__(self):
        super().__post_init__()
        if self.task in NLG_TASKS:
            self.model_path = "t5-small"
