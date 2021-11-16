from collections import OrderedDict

import transformers

if transformers.__version__.startswith("3"):
    from transformers.modeling_electra import ElectraClassificationHead
    from transformers.modeling_roberta import RobertaClassificationHead
else:
    from transformers.models.electra.modeling_electra import ElectraClassificationHead
    from transformers.models.roberta.modeling_roberta import RobertaClassificationHead

MODEL_CLASSIFICATION_HEAD_MAPPING = OrderedDict(
    [
        ("electra", ElectraClassificationHead),
        ("roberta", RobertaClassificationHead),
    ]
)


class AutoSeqClassificationHead:
    """
    This is a class for getting classification head class based on the name of the LM
    instantiated as one of the ClassificationHead classes of the library when
    created with the `~flaml.nlp.huggingface.AutoSeqClassificationHead.from_model_type_and_config` method.

    This class cannot be instantiated directly using ``__init__()`` (throws an error).
    """

    def __init__(self):
        raise EnvironmentError(
            "AutoSeqClassificationHead is designed to be instantiated "
            "using the `AutoSeqClassificationHead.from_model_type_and_config(cls, model_type, config)` methods."
        )

    @classmethod
    def from_model_type_and_config(cls, model_type, config):
        """
        Instantiate one of the classification head classes from the mode_type and model configuration.

        Args:
            model_type:
                A string, which desribes the model type, e.g., "electra"
            config (:class:`~transformers.PretrainedConfig`):
                The huggingface class of the model's configuration:

        Examples::
            >>> from transformers import AutoConfig
            >>> model_config = AutoConfig.from_pretrained("google/electra-base-discriminator")
            >>> AutoSeqClassificationHead.from_model_type_and_config("electra", model_config)
        """
        if model_type in MODEL_CLASSIFICATION_HEAD_MAPPING.keys():
            return MODEL_CLASSIFICATION_HEAD_MAPPING[model_type](config)
        raise ValueError(
            "Unrecognized configuration class {} for class {}.\n"
            "Model type should be one of {}.".format(
                config.__class__, cls.__name__, ", ".join(MODEL_CLASSIFICATION_HEAD_MAPPING.keys())
            )
        )
