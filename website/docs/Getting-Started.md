# Getting Started

<!-- ### Welcome to FLAML, a Fast Library for Automated Machine Learning & Tuning! -->

FLAML is a lightweight Python library for efficient automation of machine
learning and AI operations. It automates workflow based on large language models, machine learning models, etc.
and optimizes their performance.

### Main Features

* FLAML enables building next-gen GPT-X applications based on multi-agent conversations with minimal effort. It simplifies the orchestration, automation and optimization of a complex GPT-X workflow. It maximizes the performance of GPT-X models and augments their weakness.
* For common machine learning tasks like classification and regression, it quickly finds quality models for user-provided data with low computational resources. It is easy to customize or extend.
* It supports fast and economical automatic tuning, capable of handling large search space with heterogeneous evaluation cost and complex constraints/guidance/early stopping.

FLAML is powered by a series of [research studies](/docs/Research) from Microsoft Research and collaborators such as Penn State University, Stevens Institute of Technology, University of Washington, and University of Waterloo.

### Quickstart

Install FLAML from pip: `pip install flaml`. Find more options in [Installation](/docs/Installation).

There are several ways of using flaml:

#### (New) [Autogen](/docs/Use-Cases/Autogen)

Autogen enables the next-gen GPT-X applications with a generic multi-agent conversation framework.
It offers customizable and conversable agents which integrate LLMs, tools and human.
By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code. For example,
```python
from flaml import autogen
assistant = autogen.AssistantAgent("assistant")
user_proxy = autogen.UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Show me the YTD gain of 10 largest technology companies as of today.")
# This initiates an automated chat between the two agents to solve the task
```

Autogen also helps maximize the utility out of the expensive LLMs such as ChatGPT and GPT-4. It offers a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` with powerful functionalites like tuning, caching, error handling, templating. For example, you can optimize generations by LLM with your own tuning data, success metrics and budgets.
```python
# perform tuning
config, analysis = autogen.Completion.tune(
    data=tune_data,
    metric="success",
    mode="max",
    eval_func=eval_func,
    inference_budget=0.05,
    optimization_budget=3,
    num_samples=-1,
)
# perform inference for a test instance
response = autogen.Completion.create(context=test_instance, **config)
```

#### [Task-oriented AutoML](/docs/Use-Cases/task-oriented-automl)

With three lines of code, you can start using this economical and fast AutoML engine as a scikit-learn style estimator.

```python
from flaml import AutoML
automl = AutoML()
automl.fit(X_train, y_train, task="classification", time_budget=60)
```

It automatically tunes the hyperparameters and selects the best model from default learners such as LightGBM, XGBoost, random forest etc. for the specified time budget 60 seconds. [Customizing](/docs/Use-Cases/task-oriented-automl#customize-automlfit) the optimization metrics, learners and search spaces etc. is very easy. For example,

```python
automl.add_learner("mylgbm", MyLGBMEstimator)
automl.fit(X_train, y_train, task="classification", metric=custom_metric, estimator_list=["mylgbm"], time_budget=60)
```

#### [Tune user-defined function](/docs/Use-Cases/Tune-User-Defined-Function)

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

#### [Zero-shot AutoML](/docs/Use-Cases/Zero-Shot-AutoML)

FLAML offers a unique, seamless and effortless way to leverage AutoML for the commonly used classifiers and regressors such as LightGBM and XGBoost. For example, if you are using `lightgbm.LGBMClassifier` as your current learner, all you need to do is to replace `from lightgbm import LGBMClassifier` by:

```python
from flaml.default import LGBMClassifier
```

Then, you can use it just like you use the original `LGMBClassifier`. Your other code can remain unchanged. When you call the `fit()` function from `flaml.default.LGBMClassifier`, it will automatically instantiate a good data-dependent hyperparameter configuration for your dataset, which is expected to work better than the default configuration.

### Where to Go Next?

* Understand the use cases for [Autogen](/docs/Use-Cases/Autogen), [Task-oriented AutoML](/docs/Use-Cases/Task-Oriented-Automl), [Tune user-defined function](/docs/Use-Cases/Tune-User-Defined-Function) and [Zero-shot AutoML](/docs/Use-Cases/Zero-Shot-AutoML).
* Find code examples under "Examples": from [AutoGen - AgentChat](/docs/Examples/AutoGen-AgentChat) to [Tune - PyTorch](/docs/Examples/Tune-PyTorch).
* Learn about [research](/docs/Research) around FLAML and check [blogposts](/blog).
* Chat on [Discord](https://discord.gg/Cppx2vSPVP).

If you like our project, please give it a [star](https://github.com/microsoft/FLAML/stargazers) on GitHub. If you are interested in contributing, please read [Contributor's Guide](/docs/Contribute).

<iframe src="https://ghbtns.com/github-btn.html?user=microsoft&amp;repo=FLAML&amp;type=star&amp;count=true&amp;size=large" frameborder="0" scrolling="0" width="170" height="30" title="GitHub"></iframe>
