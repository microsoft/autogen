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
    "custom_hpo_args": {"output_dir": "data/output/"},
    "gpu_per_trial": 1,  # set to 0 if no GPU is available
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
    load_dataset("glue", "stsb", split="train[:1%]").to_pandas().iloc[0:4]
)
dev_dataset = (
    load_dataset("glue", "stsb", split="train[1%:2%]").to_pandas().iloc[0:4]
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
automl_settings["custom_hpo_args"] = {
    "model_path": "google/electra-small-discriminator",
    "output_dir": "data/output/",
    "ckpt_per_epoch": 5,
    "fp16": False,
}
automl.fit(
    X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
)
```