[![PyPI version](https://badge.fury.io/py/FLAML.svg)](https://badge.fury.io/py/FLAML)
![Conda version](https://img.shields.io/conda/vn/conda-forge/flaml)
[![Build](https://github.com/microsoft/FLAML/actions/workflows/python-package.yml/badge.svg)](https://github.com/microsoft/FLAML/actions/workflows/python-package.yml)
![Python Version](https://img.shields.io/badge/3.8%20%7C%203.9%20%7C%203.10-blue)
[![Downloads](https://pepy.tech/badge/flaml)](https://pepy.tech/project/flaml)
[![](https://img.shields.io/discord/1025786666260111483?logo=discord&style=flat)](https://discord.gg/Cppx2vSPVP)
<!-- [![Join the chat at https://gitter.im/FLAMLer/community](https://badges.gitter.im/FLAMLer/community.svg)](https://gitter.im/FLAMLer/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) -->


# A Fast Library for Automated Machine Learning & Tuning

<p align="center">
    <img src="https://github.com/microsoft/FLAML/blob/main/website/static/img/flaml.svg"  width=200>
    <br>
</p>

:fire: FLAML is highlighted in OpenAI's [cookbook](https://github.com/openai/openai-cookbook#related-resources-from-around-the-web).

:fire: [autogen](https://microsoft.github.io/FLAML/docs/Use-Cases/Auto-Generation) is released with support for ChatGPT and GPT-4, based on [Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference](https://arxiv.org/abs/2303.04673).

:fire: FLAML supports AutoML and Hyperparameter Tuning features in [Microsoft Fabric](https://learn.microsoft.com/en-us/fabric/get-started/microsoft-fabric-overview) private preview. Sign up for these features at: https://aka.ms/fabric/data-science/sign-up.


## What is FLAML
FLAML is a lightweight Python library for efficient automation of machine
learning and AI operations, including selection of
models, hyperparameters, and other tunable choices of an application (e.g., inference hyperparameters for foundation models, configurations in MLOps/LMOps workflows, pipelines, mathematical/statistical models, algorithms, computing experiments, software configurations).

* For foundation models like the GPT models, it automates the experimentation and optimization of their performance to maximize the effectiveness for applications and minimize the inference cost. FLAML enables users to build and use adaptive AI agents with minimal effort.
* For common machine learning tasks like classification and regression, it quickly finds quality models for user-provided data with low computational resources. It is easy to customize or extend. Users can find their desired customizability from a smooth range: minimal customization (computational resource budget), medium customization (e.g., search space and metric), or full customization (arbitrary training/inference/evaluation code).
* It supports fast and economical automatic tuning, capable of handling complex constraints/guidance/early stopping. FLAML is powered by a [cost-effective
hyperparameter optimization](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function/#hyperparameter-optimization-algorithm)
and model selection method invented by Microsoft Research, and many followup [research studies](https://microsoft.github.io/FLAML/docs/Research).

FLAML has a .NET implementation in [ML.NET](http://dot.net/ml), an open-source, cross-platform machine learning framework for .NET. In ML.NET, you can use FLAML via low-code solutions like [Model Builder](https://dotnet.microsoft.com/apps/machinelearning-ai/ml-dotnet/model-builder) Visual Studio extension and the cross-platform [ML.NET CLI](https://docs.microsoft.com/dotnet/machine-learning/automate-training-with-cli). Alternatively, you can use the [ML.NET AutoML API](https://www.nuget.org/packages/Microsoft.ML.AutoML/#versions-body-tab) for a code-first experience.


## Installation

### Python

FLAML requires **Python version >= 3.7**. It can be installed from pip:

```bash
pip install flaml
```

Minimal dependencies are installed without extra options. You can install extra options based on the feature you need. For example, use the following to install the dependencies needed by the [`autogen`](https://microsoft.github.io/FLAML/docs/Use-Cases/Auto-Generation) package.
```bash
pip install "flaml[autogen]"
```

Find more options in [Installation](Installation).
Each of the [`notebook examples`](https://github.com/microsoft/FLAML/tree/main/notebook) may require a specific option to be installed.

### .NET

Use the following guides to get started with FLAML in .NET:

- [Install Model Builder](https://docs.microsoft.com/dotnet/machine-learning/how-to-guides/install-model-builder?tabs=visual-studio-2022)
- [Install ML.NET CLI](https://docs.microsoft.com/dotnet/machine-learning/how-to-guides/install-ml-net-cli?tabs=windows)
- [Microsoft.AutoML](https://www.nuget.org/packages/Microsoft.ML.AutoML/0.20.0)

## Quickstart

* (New) The [autogen](https://microsoft.github.io/FLAML/docs/Use-Cases/Auto-Generation) package can help you maximize the utility out of the expensive LLMs such as ChatGPT and GPT-4, including:
    - A drop-in replacement of `openai.Completion` or `openai.ChatCompletion` with powerful functionalites like tuning, caching, templating, filtering. For example, you can optimize generations by LLM with your own tuning data, success metrics and budgets.
    ```python
    from flaml import oai

    # perform tuning
    config, analysis = oai.Completion.tune(
        data=tune_data,
        metric="success",
        mode="max",
        eval_func=eval_func,
        inference_budget=0.05,
        optimization_budget=3,
        num_samples=-1,
    )

    # perform inference for a test instance
    response = oai.Completion.create(context=test_instance, **config)
    ```
    - LLM-driven intelligent agents which can collaborately perform tasks autonomously or with human feedback, including tasks that require using tools via code.
    ```python
    assistant = AssistantAgent("assistant")
    user_proxy = UserProxyAgent("user_proxy")
    user_proxy.initiate_chat("Show me the YTD gain of 10 largest technology companies as of today.")
    ```
* With three lines of code, you can start using this economical and fast
AutoML engine as a [scikit-learn style estimator](https://microsoft.github.io/FLAML/docs/Use-Cases/Task-Oriented-AutoML).

```python
from flaml import AutoML
automl = AutoML()
automl.fit(X_train, y_train, task="classification")
```

* You can restrict the learners and use FLAML as a fast hyperparameter tuning
tool for XGBoost, LightGBM, Random Forest etc. or a [customized learner](https://microsoft.github.io/FLAML/docs/Use-Cases/Task-Oriented-AutoML#estimator-and-search-space).

```python
automl.fit(X_train, y_train, task="classification", estimator_list=["lgbm"])
```

* You can also run generic hyperparameter tuning for a [custom function](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function).

```python
from flaml import tune
tune.run(evaluation_function, config={…}, low_cost_partial_config={…}, time_budget_s=3600)
```

* [Zero-shot AutoML](https://microsoft.github.io/FLAML/docs/Use-Cases/Zero-Shot-AutoML) allows using the existing training API from lightgbm, xgboost etc. while getting the benefit of AutoML in choosing high-performance hyperparameter configurations per task.

```python
from flaml.default import LGBMRegressor

# Use LGBMRegressor in the same way as you use lightgbm.LGBMRegressor.
estimator = LGBMRegressor()
# The hyperparameters are automatically set according to the training data.
estimator.fit(X_train, y_train)
```

## Documentation

You can find a detailed documentation about FLAML [here](https://microsoft.github.io/FLAML/) where you can find the API documentation, use cases and examples.

In addition, you can find:

- [Research](https://microsoft.github.io/FLAML/docs/Research) and [blogposts](https://microsoft.github.io/FLAML/blog) around FLAML.

- [Discord](https://discord.gg/Cppx2vSPVP).

- [Contributing guide](https://microsoft.github.io/FLAML/docs/Contribute).

- ML.NET documentation and tutorials for [Model Builder](https://learn.microsoft.com/dotnet/machine-learning/tutorials/predict-prices-with-model-builder), [ML.NET CLI](https://learn.microsoft.com/dotnet/machine-learning/tutorials/sentiment-analysis-cli), and [AutoML API](https://learn.microsoft.com/dotnet/machine-learning/how-to-guides/how-to-use-the-automl-api).

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

If you are new to GitHub [here](https://help.github.com/categories/collaborating-with-issues-and-pull-requests/) is a detailed help source on getting involved with development on GitHub.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
