# Hyperparameter Optimization for Huggingface Transformers

Fine-tuning pre-trained language models based on the transformers library.

An example:

```python
from flaml import AutoML
import pandas as pd

train_dataset = pd.read_csv("data/input/train.tsv", delimiter="\t", quoting=3)
dev_dataset = pd.read_csv("data/input/dev.tsv", delimiter="\t", quoting=3)
test_dataset = pd.read_csv("data/input/test.tsv", delimiter="\t", quoting=3)

custom_sent_keys = ["#1 String", "#2 String"]
label_key = "Quality"

X_train = train_dataset[custom_sent_keys]
y_train = train_dataset[label_key]

X_val = dev_dataset[custom_sent_keys]
y_val = dev_dataset[label_key]

X_test = test_dataset[custom_sent_keys]

automl = AutoML()

automl_settings = {
    "gpu_per_trial": 0,  # use a value larger than 0 for GPU training
    "max_iter": 10,
    "time_budget": 300,
    "task": "seq-classification",
    "metric": "accuracy",
}

automl_settings["custom_hpo_args"] = {
    "model_path": "google/electra-small-discriminator",
    "output_dir": "data/output/",
    "ckpt_per_epoch": 1,
}

automl.fit(
    X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
)
automl.predict(X_test)

```

The current use cases that are supported:

1. A simplified version of fine-tuning the GLUE dataset using HuggingFace;
2. For selecting better search space for fine-tuning the GLUE dataset;
3. Use the search algorithms in flaml for more efficient fine-tuning of HuggingFace.

The use cases that can be supported in future:

1. HPO fine-tuning for text generation;
2. HPO fine-tuning for question answering.

## Troubleshooting fine-tuning HPO for pre-trained language models

To reproduce the results for our ACL2021 paper:

* [An Empirical Study on Hyperparameter Optimization for Fine-Tuning Pre-trained Language Models](https://arxiv.org/abs/2106.09204). Xueqing Liu, Chi Wang. ACL-IJCNLP 2021.

```bibtex
@inproceedings{liu2021hpo,
    title={An Empirical Study on Hyperparameter Optimization for Fine-Tuning Pre-trained Language Models},
    author={Xueqing Liu and Chi Wang},
    year={2021},
    booktitle={ACL-IJCNLP},
}
```

Please refer to the following jupyter notebook: [Troubleshooting HPO for fine-tuning pre-trained language models](https://github.com/microsoft/FLAML/blob/main/notebook/research/acl2021.ipynb)