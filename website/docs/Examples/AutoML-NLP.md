# AutoML - NLP

### Requirements

This example requires GPU. Install the [nlp] option:
```python
pip install "flaml[nlp]"
```

### A simple sequence classification example

```python
from flaml import AutoML
from datasets import load_dataset

train_dataset = load_dataset("glue", "mrpc", split="train").to_pandas()
dev_dataset = load_dataset("glue", "mrpc", split="validation").to_pandas()
test_dataset = load_dataset("glue", "mrpc", split="test").to_pandas()
custom_sent_keys = ["sentence1", "sentence2"]
label_key = "label"
X_train, y_train = train_dataset[custom_sent_keys], train_dataset[label_key]
X_val, y_val = dev_dataset[custom_sent_keys], dev_dataset[label_key]
X_test = test_dataset[custom_sent_keys]

automl = AutoML()
automl_settings = {
    "time_budget": 100,
    "task": "seq-classification",
    "fit_kwargs_by_estimator": {  
        "transformer":
       {
           "output_dir": "data/output/"  # if model_path is not set, the default model is facebook/muppet-roberta-base: https://huggingface.co/facebook/muppet-roberta-base
       }
    },  # setting the huggingface arguments: output directory
    "gpu_per_trial": 1,                         # set to 0 if no GPU is available
}
automl.fit(X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings)
automl.predict(X_test)
```

#### Sample output

```
[flaml.automl: 12-06 08:21:39] {1943} INFO - task = seq-classification
[flaml.automl: 12-06 08:21:39] {1945} INFO - Data split method: stratified
[flaml.automl: 12-06 08:21:39] {1949} INFO - Evaluation method: holdout
[flaml.automl: 12-06 08:21:39] {2019} INFO - Minimizing error metric: 1-accuracy
[flaml.automl: 12-06 08:21:39] {2071} INFO - List of ML learners in AutoML Run: ['transformer']
[flaml.automl: 12-06 08:21:39] {2311} INFO - iteration 0, current learner transformer
{'data/output/train_2021-12-06_08-21-53/train_8947b1b2_1_n=1e-06,s=9223372036854775807,e=1e-05,s=-1,s=0.45765,e=32,d=42,o=0.0,y=0.0_2021-12-06_08-21-53/checkpoint-53': 53}
[flaml.automl: 12-06 08:22:56] {2424} INFO - Estimated sufficient time budget=766860s. Estimated necessary time budget=767s.
[flaml.automl: 12-06 08:22:56] {2499} INFO -  at 76.7s, estimator transformer's best error=0.1740,      best estimator transformer's best error=0.1740
[flaml.automl: 12-06 08:22:56] {2606} INFO - selected model: <flaml.nlp.huggingface.trainer.TrainerForAuto object at 0x7f49ea8414f0>
[flaml.automl: 12-06 08:22:56] {2100} INFO - fit succeeded
[flaml.automl: 12-06 08:22:56] {2101} INFO - Time taken to find the best model: 76.69802761077881
[flaml.automl: 12-06 08:22:56] {2112} WARNING - Time taken to find the best model is 77% of the provided time budget and not all estimators' hyperparameter search converged. Consider increasing the time budget.
```

### A simple sequence regression example

```python
from flaml import AutoML
from datasets import load_dataset

train_dataset = (
    load_dataset("glue", "stsb", split="train").to_pandas()
)
dev_dataset = (
    load_dataset("glue", "stsb", split="train").to_pandas()
)
custom_sent_keys = ["sentence1", "sentence2"]
label_key = "label"
X_train = train_dataset[custom_sent_keys]
y_train = train_dataset[label_key]
X_val = dev_dataset[custom_sent_keys]
y_val = dev_dataset[label_key]

automl = AutoML()
automl_settings = {
    "gpu_per_trial": 0,
    "time_budget": 20,
    "task": "seq-regression",
    "metric": "rmse",
}
automl_settings["fit_kwargs_by_estimator"] = {  # setting the huggingface arguments
    "transformer": {
        "model_path": "google/electra-small-discriminator", # if model_path is not set, the default model is facebook/muppet-roberta-base: https://huggingface.co/facebook/muppet-roberta-base
        "output_dir": "data/output/",                       # setting the output directory
        "ckpt_per_epoch": 5,                                # setting the number of checkpoints per epoch
        "fp16": False,  
    }   # setting whether to use FP16
}
automl.fit(
    X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
)
```

#### Sample output

```
[flaml.automl: 12-20 11:47:28] {1965} INFO - task = seq-regression
[flaml.automl: 12-20 11:47:28] {1967} INFO - Data split method: uniform
[flaml.automl: 12-20 11:47:28] {1971} INFO - Evaluation method: holdout
[flaml.automl: 12-20 11:47:28] {2063} INFO - Minimizing error metric: rmse
[flaml.automl: 12-20 11:47:28] {2115} INFO - List of ML learners in AutoML Run: ['transformer']
[flaml.automl: 12-20 11:47:28] {2355} INFO - iteration 0, current learner transformer
```

### A simple summarization example

```python
from flaml import AutoML
from datasets import load_dataset

train_dataset = (
    load_dataset("xsum", split="train").to_pandas()
)
dev_dataset = (
    load_dataset("xsum", split="validation").to_pandas()
)
custom_sent_keys = ["document"]
label_key = "summary"

X_train = train_dataset[custom_sent_keys]
y_train = train_dataset[label_key]

X_val = dev_dataset[custom_sent_keys]
y_val = dev_dataset[label_key]

automl = AutoML()
automl_settings = {
    "gpu_per_trial": 1,
    "time_budget": 20,
    "task": "summarization",
    "metric": "rouge1",
}
automl_settings["fit_kwargs_by_estimator"] = {      # setting the huggingface arguments
    "transformer": {
        "model_path": "t5-small",             # if model_path is not set, the default model is t5-small: https://huggingface.co/t5-small
        "output_dir": "data/output/",         # setting the output directory
        "ckpt_per_epoch": 5,                  # setting the number of checkpoints per epoch
        "fp16": False,  
    } # setting whether to use FP16
}
automl.fit(
    X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
)
```
#### Sample Output

```
[flaml.automl: 12-20 11:44:03] {1965} INFO - task = summarization
[flaml.automl: 12-20 11:44:03] {1967} INFO - Data split method: uniform
[flaml.automl: 12-20 11:44:03] {1971} INFO - Evaluation method: holdout
[flaml.automl: 12-20 11:44:03] {2063} INFO - Minimizing error metric: -rouge
[flaml.automl: 12-20 11:44:03] {2115} INFO - List of ML learners in AutoML Run: ['transformer']
[flaml.automl: 12-20 11:44:03] {2355} INFO - iteration 0, current learner transformer
loading configuration file https://huggingface.co/t5-small/resolve/main/config.json from cache at /home/xliu127/.cache/huggingface/transformers/fe501e8fd6425b8ec93df37767fcce78ce626e34cc5edc859c662350cf712e41.406701565c0afd9899544c1cb8b93185a76f00b31e5ce7f6e18bbaef02241985
Model config T5Config {
  "_name_or_path": "t5-small",
  "architectures": [
    "T5WithLMHeadModel"
  ],
  "d_ff": 2048,
  "d_kv": 64,
  "d_model": 512,
  "decoder_start_token_id": 0,
  "dropout_rate": 0.1,
  "eos_token_id": 1,
  "feed_forward_proj": "relu",
  "initializer_factor": 1.0,
  "is_encoder_decoder": true,
  "layer_norm_epsilon": 1e-06,
  "model_type": "t5",
  "n_positions": 512,
  "num_decoder_layers": 6,
  "num_heads": 8,
  "num_layers": 6,
  "output_past": true,
  "pad_token_id": 0,
  "relative_attention_num_buckets": 32,
  "task_specific_params": {
    "summarization": {
      "early_stopping": true,
      "length_penalty": 2.0,
      "max_length": 200,
      "min_length": 30,
      "no_repeat_ngram_size": 3,
      "num_beams": 4,
      "prefix": "summarize: "
    },
    "translation_en_to_de": {
      "early_stopping": true,
      "max_length": 300,
      "num_beams": 4,
      "prefix": "translate English to German: "
    },
    "translation_en_to_fr": {
      "early_stopping": true,
      "max_length": 300,
      "num_beams": 4,
      "prefix": "translate English to French: "
    },
    "translation_en_to_ro": {
      "early_stopping": true,
      "max_length": 300,
      "num_beams": 4,
      "prefix": "translate English to Romanian: "
    }
  },
  "transformers_version": "4.14.1",
  "use_cache": true,
  "vocab_size": 32128
}
```

For tasks that are not currently supported, use `flaml.tune` for [customized tuning](Tune-HuggingFace).

### Link to Jupyter notebook

To run these examples in our Jupyter notebook, please go to:

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/automl_nlp.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/automl_nlp.ipynb)