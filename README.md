[![PyPI version](https://badge.fury.io/py/FLAML.svg)](https://badge.fury.io/py/FLAML)
[![Build](https://github.com/microsoft/FLAML/actions/workflows/python-package.yml/badge.svg)](https://github.com/microsoft/FLAML/actions/workflows/python-package.yml)
![Python Version](https://img.shields.io/badge/3.6%20%7C%203.7%20%7C%203.8-blue)
[![Downloads](https://pepy.tech/badge/flaml/month)](https://pepy.tech/project/flaml)

# FLAML - Fast and Lightweight AutoML

<p align="center">
    <img src="https://github.com/microsoft/FLAML/raw/v0.2.2/docs/images/FLAML.png"  width=200>
    <br>
</p>

FLAML is a lightweight Python library that finds accurate machine
learning models automatically, efficiently and economically. It frees users from selecting
learners and hyperparameters for each learner. It is fast and cheap.
The simple and lightweight design makes it easy to extend, such as
adding customized learners or metrics. FLAML is powered by a new, [cost-effective
hyperparameter optimization](https://github.com/microsoft/FLAML/tree/main/flaml/tune)
and learner selection method invented by Microsoft Research.
FLAML is easy to use:

* With three lines of code, you can start using this economical and fast
AutoML engine as a scikit-learn style estimator.
```python
from flaml import AutoML
automl = AutoML()
automl.fit(X_train, y_train, task="classification")
```

* You can restrict the learners and use FLAML as a fast hyperparameter tuning
tool for XGBoost, LightGBM, Random Forest etc. or a customized learner.
```python
automl.fit(X_train, y_train, task="classification", estimator_list=["lgbm"])
```

* You can also run generic ray-tune style hyperparameter tuning for a custom function.
```python
from flaml import tune
tune.run(train_with_config, config={…}, init_config={…}, time_budget_s=3600)
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
# Initialize an AutoML instance
automl = AutoML()
# Specify automl goal and constraint
automl_settings = {
    "time_budget": 10,  # in seconds
    "metric": 'accuracy',
    "task": 'classification',
    "log_file_name": "test/iris.log",
}
X_train, y_train = load_iris(return_X_y=True)
# Train with labeled input data
automl.fit(X_train=X_train, y_train=y_train,
                        **automl_settings)
# Predict
print(automl.predict_proba(X_train))
# Export the best model
print(automl.model)
```

A basic regression example.

```python
from flaml import AutoML
from sklearn.datasets import load_boston
# Initialize an AutoML instance
automl = AutoML()
# Specify automl goal and constraint
automl_settings = {
    "time_budget": 10,  # in seconds
    "metric": 'r2',
    "task": 'regression',
    "log_file_name": "test/boston.log",
}
X_train, y_train = load_boston(return_X_y=True)
# Train with labeled input data
automl.fit(X_train=X_train, y_train=y_train,
                        **automl_settings)
# Predict
print(automl.predict(X_train))
# Export the best model
print(automl.model)
```

More examples can be found in [notebooks](https://github.com/microsoft/FLAML/tree/main/notebook/).

## Documentation

The API documentation is [here](https://microsoft.github.io/FLAML/).

Read more about the 
hyperparameter optimization methods
in FLAML [here](https://github.com/microsoft/FLAML/tree/main/flaml/tune). They can be used beyond the AutoML context. 
And they can be used in distributed HPO frameworks such as ray tune or nni.

For more technical details, please check our papers.

* [FLAML: A Fast and Lightweight AutoML Library](https://arxiv.org/abs/1911.04706). Chi Wang, Qingyun Wu, Markus Weimer, Erkang Zhu. To appear in MLSys, 2021.
```
@inproceedings{wang2021flaml,
    title={FLAML: A Fast and Lightweight AutoML Library},
    author={Chi Wang and Qingyun Wu and Markus Weimer and Erkang Zhu},
    year={2021},
    booktitle={MLSys},
}
```
* [Frugal Optimization for Cost-related Hyperparameters](https://arxiv.org/abs/2005.01571). Qingyun Wu, Chi Wang, Silu Huang. AAAI 2021.
* Economical Hyperparameter Optimization With Blended Search Strategy. Chi Wang, Qingyun Wu, Silu Huang, Amin Saied. To appear in ICLR 2021.

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

Contributors (alphabetical order): Sebastien Bubeck, Surajit Chaudhuri, Nadiia Chepurko, Ofer Dekel, Alex Deng, Anshuman Dutt, Nicolo Fusi, Jianfeng Gao, Johannes Gehrke, Silu Huang, Dongwoo Kim, Christian Konig, John Langford, Amin Saied, Neil Tenenholtz, Markus Weimer, Haozhe Zhang, Erkang Zhu.

## License

[MIT License](LICENSE)
