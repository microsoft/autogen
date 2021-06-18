# Hyperparameter Optimization for Huggingface Transformers

AutoTransformers is an AutoML class for fine-tuning pre-trained language models based on the transformers library. 

An example of using AutoTransformers:

```python
from flaml.nlp.autotransformers import AutoTransformers

autohf = AutoTransformers()
preparedata_setting = {
        "dataset_subdataset_name": "glue:mrpc",
        "pretrained_model_size": "electra-base-discriminator:base",
        "data_root_path": "data/",
        "max_seq_length": 128,
        }
autohf.prepare_data(**preparedata_setting)
autohf_settings = {"resources_per_trial": {"gpu": 1, "cpu": 1},
                    "num_samples": -1, # unlimited sample size
                    "time_budget": 3600,
                    "ckpt_per_epoch": 1,
                    "fp16": False,
                   }
validation_metric, analysis = \
    autohf.fit(**autohf_settings,)

```

The current use cases that are supported:
1. A simplified version of fine-tuning the GLUE dataset using HuggingFace;
2. For selecting better search space for fine-tuning the GLUE dataset;
3. Use the search algorithms in flaml for more efficient fine-tuning of HuggingFace;

The use cases that can be supported in future:
1. HPO fine-tuning for text generation;
2. HPO fine-tuning for question answering;

### Troubleshooting fine-tuning HPO for pre-trained language models

To reproduce the results for our ACL2021 paper:

*[An Empirical Study on Hyperparameter Optimization for Fine-Tuning Pre-trained Language Models](https://arxiv.org/abs/2106.09204). Xueqing Liu, Chi Wang. To appear in ACL-IJCNLP 2021*

Please refer to the following jupyter notebook: [Troubleshooting HPO for fine-tuning pre-trained language models](https://github.com/microsoft/FLAML/blob/main/notebook/research/acl2021.ipynb)