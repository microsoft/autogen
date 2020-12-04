# FLAML - Fast and Lightweight AutoML

FLAML is a Python library designed to automatically produce accurate machine
learning models with low computational cost. It frees users from selecting
learners and hyperparameters for each learner. It is fast and cheap.
The simple and lightweight design makes it easy to extend, such as
adding customized learners or metrics. FLAML is powered by a new, cost-effective
hyperparameter optimization and learner selection method invented by
Microsoft Research.
FLAML is easy to use:

1. With three lines of code, you can start using this economical and fast
AutoML engine as a scikit-learn style estimator.
```python
from flaml import AutoML
automl = AutoML()
automl.fit(X_train, y_train, task="classification")
```

2. You can restrict the learners and use FLAML as a fast hyperparameter tuning
tool for XGBoost, LightGBM, Random Forest etc. or a customized learner.
```python
automl.fit(X_train, y_train, task="classification", estimator_list=["lgbm"])
```

3. You can embed FLAML in self-tuning software for just-in-time tuning with
low latency & resource consumption.
```python
automl.fit(X_train, y_train, task="regression", time_budget=60)
```

## Installation

FLAML requires **Python version >= 3.6**. It can be installed from pip:

```bash
pip install flaml
```

To run the [`notebook example`](https://github.com/microsoft/FLAML/tree/main/notebook),
install flaml with the [notebook] option:

```bash
pip install flaml[notebook]
```

## Examples

A basic classification example.

```python
from flaml import AutoML
from sklearn.datasets import load_iris
# Initialize the FLAML learner.
automl = AutoML()
# Provide configurations.
automl_settings = {
    "time_budget": 10,  # in seconds
    "metric": 'accuracy',
    "task": 'classification',
    "log_file_name": "test/iris.log",
}
X_train, y_train = load_iris(return_X_y=True)
# Train with labeled input data.
automl.fit(X_train=X_train, y_train=y_train,
                        **automl_settings)
# Predict
print(automl.predict_proba(X_train))
# Export the best model.
print(automl.model)
```

A basic regression example.

```python
from flaml import AutoML
from sklearn.datasets import load_boston
# Initialize the FLAML learner.
automl = AutoML()
# Provide configurations.
automl_settings = {
    "time_budget": 10,  # in seconds
    "metric": 'r2',
    "task": 'regression',
    "log_file_name": "test/boston.log",
}
X_train, y_train = load_boston(return_X_y=True)
# Train with labeled input data.
automl.fit(X_train=X_train, y_train=y_train,
                        **automl_settings)
# Predict
print(automl.predict(X_train))
# Export the best model.
print(automl.model)
```

More examples: see the [notebook](https://github.com/microsoft/FLAML/tree/main/notebook/flaml_demo.ipynb)

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Authors

* Chi Wang
* Qingyun Wu
* Erkang Zhu

Contributors: Markus Weimer, Silu Huang, Haozhe Zhang, Alex Deng.

## License

[MIT License](LICENSE)
