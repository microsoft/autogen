
[![PyPI version](https://badge.fury.io/py/pyautogen.svg)](https://badge.fury.io/py/pyautogen)
[![Build](https://github.com/microsoft/autogen/actions/workflows/python-package.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/python-package.yml)
![Python Version](https://img.shields.io/badge/3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)
[![](https://img.shields.io/discord/1025786666260111483?logo=discord&style=flat)](https://discord.gg/pAbnFJrkgZ)

This project is a spinoff from [FLAML](https://github.com/microsoft/FLAML).

# AutoGen

<!-- <p align="center">
    <img src="https://github.com/microsoft/autogen/blob/main/website/static/img/flaml.svg"  width=200>
    <br>
</p> -->

:fire: autogen has graduated from [FLAML](https://github.com/microsoft/FLAML) into a new project.

<!-- :fire: Heads-up: We're preparing to migrate [autogen](https://microsoft.github.io/FLAML/docs/Use-Cases/Autogen) into a dedicated github repository. Alongside this move, we'll also launch a dedicated Discord server and a website for comprehensive documentation.

:fire: FLAML is highlighted in OpenAI's [cookbook](https://github.com/openai/openai-cookbook#related-resources-from-around-the-web).

:fire: [autogen](https://microsoft.github.io/autogen/) is released with support for ChatGPT and GPT-4, based on [Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference](https://arxiv.org/abs/2303.04673).

:fire: FLAML supports Code-First AutoML & Tuning – Private Preview in [Microsoft Fabric Data Science](https://learn.microsoft.com/en-us/fabric/data-science/). -->


## What is AutoGen

AutoGen is a framework that enables development of LLM applications using multiple agents that can converse with each other to solve task. AutoGen agents are customizable, conversable, and seamlessly allow human participation. They can operate in various modes that employ combinations of LLMs, human inputs, and tools.

![AutoGen Overview](https://github.com/microsoft/autogen/blob/main/website/static/img/autogen_agentchat.png)

* AutoGen enables building next-gen LLM applications based on **multi-agent conversations** with minimal effort. It simplifies the orchestration, automation and optimization of a complex LLM workflow. It maximizes the performance of LLM models and overcome their weaknesses.
* It supports **diverse conversation patterns** for complex workflows. With customizable and conversable agents, developers can use AutoGen to build a wide range of conversation patterns concerning conversation autonomy,
the number of agents, and agent conversation topology.
* It provides a collection of working systems with different complexities. These systems span a **wide range of applications** from various domains and complexities. They demonstrate how AutoGen can easily support different conversation patterns.
* AutoGen provides a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` as an **enhanced inference API**. It allows easy performance tuning, utilities like API unification & caching, and advanced usage patterns, such as error handling, multi-config inference, context programming etc.

AutoGen is powered by collaborative [research studies](https://microsoft.github.io/autogen/docs/Research) from Microsoft, Penn State University, and University of Washington.

## Installation

AutoGen requires **Python version >= 3.8**. It can be installed from pip:

```bash
pip install pyautogen
```

Minimal dependencies are installed without extra options. You can install extra options based on the feature you need.
For example, use the following to install the dependencies needed by the [`blendsearch`](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function#blendsearch-economical-hyperparameter-optimization-with-blended-search-strategy) option.
```bash
pip install "pyautogen[blendsearch]"
```

Find more options in [Installation](https://microsoft.github.io/autogen/docs/Installation).
<!-- Each of the [`notebook examples`](https://github.com/microsoft/autogen/tree/main/notebook) may require a specific option to be installed. -->

## Quickstart

* Autogen enables the next-gen LLM applications with a generic multi-agent conversation framework. It offers customizable and conversable agents which integrate LLMs, tools and human.
By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code. For example,
```python
from autogen import AssistantAgent, UserProxyAgent
assistant = AssistantAgent("assistant")
user_proxy = UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Plot a chart of META and TESLA stock price change YTD.")
# This initiates an automated chat between the two agents to solve the task
```

The figure below shows an example conversation flow with AutoGen.
![Agent Chat Example](https://github.com/microsoft/autogen/blob/main/website/static/img/chat_example.png)

* Autogen also helps maximize the utility out of the expensive LLMs such as ChatGPT and GPT-4. It offers a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` with powerful functionalites like tuning, caching, error handling, templating. For example, you can optimize generations by LLM with your own tuning data, success metrics and budgets.
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

## Documentation

You can find a detailed documentation about AutoGen [here](https://microsoft.github.io/autogen/).

In addition, you can find:

- [Research](https://microsoft.github.io/autogen/docs/Research) and [blogposts](https://microsoft.github.io/autogen/blog) around AutoGen.

- [Discord](https://discord.gg/pAbnFJrkgZ).

- [Contributing guide](https://microsoft.github.io/autogen/docs/Contribute).

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

# Legal Notices

Microsoft and any contributors grant you a license to the Microsoft documentation and other content
in this repository under the [Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode),
see the [LICENSE](LICENSE) file, and grant you a license to any code in the repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE-CODE](LICENSE-CODE) file.

Microsoft, Windows, Microsoft Azure and/or other Microsoft products and services referenced in the documentation
may be either trademarks or registered trademarks of Microsoft in the United States and/or other countries.
The licenses for this project do not grant you rights to use any Microsoft names, logos, or trademarks.
Microsoft's general trademark guidelines can be found at http://go.microsoft.com/fwlink/?LinkID=254653.

Privacy information can be found at https://privacy.microsoft.com/en-us/

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel or otherwise.
