# Getting Started

<!-- ### Welcome to FLAML, a Fast Library for Automated Machine Learning & Tuning! -->

FLAML is a lightweight Python library that finds accurate machine
learning models automatically, efficiently and economically. It frees users from selecting models and hyperparameters for each model.

### Main Features

1. For common machine learning or AI tasks like classification, regression, and generation, it quickly finds quality models for user-provided data with low computational resources. It supports both classical machine learning models and deep neural networks, including large language models such as the OpenAI GPT-3 models.

2. It is easy to customize or extend. Users can find their desired customizability from a smooth range: minimal customization (computational resource budget), medium customization (e.g., scikit-style learner, search space and metric), or full customization (arbitrary training and evaluation code). Users can customize only when and what they need to, and leave the rest to the library.

3. It supports fast and economical automatic tuning, capable of handling large search space with heterogeneous evaluation cost and complex constraints/guidance/early stopping. FLAML is powered by a new, [cost-effective
hyperparameter optimization](Use-Cases/Tune-User-Defined-Function#hyperparameter-optimization-algorithm)
and model selection method invented by Microsoft Research, and many followup [research studies](Research).

### Quickstart

Install FLAML from pip: `pip install flaml`. Find more options in [Installation](Installation).

There are several ways of using flaml:

#### [Task-oriented AutoML](Use-Cases/task-oriented-automl)

For example, with three lines of code, you can start using this economical and fast AutoML engine as a scikit-learn style estimator.

```python
from flaml import AutoML
automl = AutoML()
automl.fit(X_train, y_train, task="classification", time_budget=60)
```

It automatically tunes the hyperparameters and selects the best model from default learners such as LightGBM, XGBoost, random forest etc. for the specified time budget 60 seconds. [Customizing](Use-Cases/task-oriented-automl#customize-automlfit) the optimization metrics, learners and search spaces etc. is very easy. For example,

```python
automl.add_learner("mylgbm", MyLGBMEstimator)
automl.fit(X_train, y_train, task="classification", metric=custom_metric, estimator_list=["mylgbm"], time_budget=60)
```

#### [Tune user-defined function](Use-Cases/Tune-User-Defined-Function)

You can run generic hyperparameter tuning for a custom function (machine learning or beyond). For example,

```python
from flaml import tune
from flaml.automl.model import LGBMEstimator


def train_lgbm(config: dict) -> dict:
    # convert config dict to lgbm params
    params = LGBMEstimator(**config).params
    # train the model
    train_set = lightgbm.Dataset(csv_file_name)
    model = lightgbm.train(params, train_set)
    # evaluate the model
    pred = model.predict(X_test)
    mse = mean_squared_error(y_test, pred)
    # return eval results as a dictionary
    return {"mse": mse}


# load a built-in search space from flaml
flaml_lgbm_search_space = LGBMEstimator.search_space(X_train.shape)
# specify the search space as a dict from hp name to domain; you can define your own search space same way
config_search_space = {hp: space["domain"] for hp, space in flaml_lgbm_search_space.items()}
# give guidance about hp values corresponding to low training cost, i.e., {"n_estimators": 4, "num_leaves": 4}
low_cost_partial_config = {
    hp: space["low_cost_init_value"]
    for hp, space in flaml_lgbm_search_space.items()
    if "low_cost_init_value" in space
}
# run the tuning, minimizing mse, with total time budget 3 seconds
analysis = tune.run(
    train_lgbm, metric="mse", mode="min", config=config_search_space,
    low_cost_partial_config=low_cost_partial_config, time_budget_s=3, num_samples=-1,
)
```
Please see this [script](https://github.com/microsoft/FLAML/blob/main/test/tune_example.py) for the complete version of the above example.

#### [Zero-shot AutoML](Use-Cases/Zero-Shot-AutoML)

FLAML offers a unique, seamless and effortless way to leverage AutoML for the commonly used classifiers and regressors such as LightGBM and XGBoost. For example, if you are using `lightgbm.LGBMClassifier` as your current learner, all you need to do is to replace `from lightgbm import LGBMClassifier` by:

```python
from flaml.default import LGBMClassifier
```

Then, you can use it just like you use the original `LGMBClassifier`. Your other code can remain unchanged. When you call the `fit()` function from `flaml.default.LGBMClassifier`, it will automatically instantiate a good data-dependent hyperparameter configuration for your dataset, which is expected to work better than the default configuration.

### Where to Go Next?

* Understand the use cases for [Task-oriented AutoML](Use-Cases/task-oriented-automl), [Tune user-defined function](Use-Cases/Tune-User-Defined-Function) and [Zero-shot AutoML](Use-Cases/Zero-Shot-AutoML).
* Find code examples under "Examples": from [AutoML - Classification](Examples/AutoML-Classification) to [Tune - PyTorch](Examples/Tune-PyTorch).
* Find [talks](https://www.youtube.com/channel/UCfU0zfFXHXdAd5x-WvFBk5A) and [tutorials](https://github.com/microsoft/FLAML/tree/tutorial/tutorial) about FLAML.
* Learn about [research](Research) around FLAML.
* Refer to [SDK](reference/automl/automl) and [FAQ](FAQ).

If you like our project, please give it a [star](https://github.com/microsoft/FLAML/stargazers) on GitHub. If you are interested in contributing, please read [Contributor's Guide](Contribute).

<iframe src="https://ghbtns.com/github-btn.html?user=microsoft&amp;repo=FLAML&amp;type=star&amp;count=true&amp;size=large" frameborder="0" scrolling="0" width="170" height="30" title="GitHub"></iframe>
