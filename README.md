[![PyPI version](https://badge.fury.io/py/pyautogen.svg)](https://badge.fury.io/py/pyautogen)
[![Build](https://github.com/microsoft/autogen/actions/workflows/python-package.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/python-package.yml)
![Python Version](https://img.shields.io/badge/3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)
[![](https://img.shields.io/discord/1153072414184452236?logo=discord&style=flat)](https://discord.gg/pAbnFJrkgZ)

This project is a spinoff from [FLAML](https://github.com/microsoft/FLAML).

# AutoGen

<!-- <p align="center">
    <img src="https://github.com/microsoft/autogen/blob/main/website/static/img/flaml.svg"  width=200>
    <br>
</p> -->

:fire: autogen has graduated from [FLAML](https://github.com/microsoft/FLAML) into a new project.

<!-- :fire: Heads-up: We're preparing to migrate [autogen](https://microsoft.github.io/FLAML/docs/Use-Cases/Autogen) into a dedicated Github repository. Alongside this move, we'll also launch a dedicated Discord server and a website for comprehensive documentation.

:fire: FLAML is highlighted in OpenAI's [cookbook](https://github.com/openai/openai-cookbook#related-resources-from-around-the-web).

:fire: [autogen](https://microsoft.github.io/autogen/) is released with support for ChatGPT and GPT-4, based on [Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference](https://arxiv.org/abs/2303.04673).

:fire: FLAML supports Code-First AutoML & Tuning – Private Preview in [Microsoft Fabric Data Science](https://learn.microsoft.com/en-us/fabric/data-science/). -->

## What is AutoGen

AutoGen is a framework that enables the development of LLM applications using multiple agents that can converse with each other to solve tasks. AutoGen agents are customizable, conversable, and seamlessly allow human participation. They can operate in various modes that employ combinations of LLMs, human inputs, and tools.

![AutoGen Overview](https://github.com/microsoft/autogen/blob/main/website/static/img/autogen_agentchat.png)

- AutoGen enables building next-gen LLM applications based on **multi-agent conversations** with minimal effort. It simplifies the orchestration, automation, and optimization of a complex LLM workflow. It maximizes the performance of LLM models and overcomes their weaknesses.
- It supports **diverse conversation patterns** for complex workflows. With customizable and conversable agents, developers can use AutoGen to build a wide range of conversation patterns concerning conversation autonomy,
  the number of agents, and agent conversation topology.
- It provides a collection of working systems with different complexities. These systems span a **wide range of applications** from various domains and complexities. This demonstrates how AutoGen can easily support diverse conversation patterns.
- AutoGen provides a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` as an **enhanced inference API**. It allows easy performance tuning, utilities like API unification and caching, and advanced usage patterns, such as error handling, multi-config inference, context programming, etc.

AutoGen is powered by collaborative [research studies](https://microsoft.github.io/autogen/docs/Research) from Microsoft, Penn State University, and the University of Washington.

## Installation

AutoGen requires **Python version >= 3.8**. It can be installed from pip:

```bash
pip install pyautogen
```

Minimal dependencies are installed without extra options. You can install extra options based on the feature you need.

<!-- For example, use the following to install the dependencies needed by the [`blendsearch`](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function#blendsearch-economical-hyperparameter-optimization-with-blended-search-strategy) option.
```bash
pip install "pyautogen[blendsearch]"
``` -->

Find more options in [Installation](https://microsoft.github.io/autogen/docs/Installation).

<!-- Each of the [`notebook examples`](https://github.com/microsoft/autogen/tree/main/notebook) may require a specific option to be installed. -->

For [code execution](https://microsoft.github.io/autogen/docs/FAQ/#code-execution), we strongly recommend installing the python docker package, and using docker.

For LLM inference configurations, check the [FAQ](https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints).

## Quickstart

## Multi-Agent Conversation Framework

Autogen enables the next-gen LLM applications with a generic multi-agent conversation framework. It offers customizable and conversable agents that integrate LLMs, tools, and humans.
By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code.

Features of this use case include:

- **Multi-agent conversations**: AutoGen agents can communicate with each other to solve tasks. This allows for more complex and sophisticated applications than would be possible with a single LLM.
- **Customization**: AutoGen agents can be customized to meet the specific needs of an application. This includes the ability to choose the LLMs to use, the types of human input to allow, and the tools to employ.
- **Human participation**: AutoGen seamlessly allows human participation. This means that humans can provide input and feedback to the agents as needed.

For [example](https://github.com/microsoft/autogen/blob/main/test/twoagent.py),

```python
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
# Load LLM inference endpoints from an env variable or a file
# See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample
config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
user_proxy = UserProxyAgent("user_proxy", code_execution_config={"work_dir": "coding"})
user_proxy.initiate_chat(assistant, message="Plot a chart of NVDA and TESLA stock price change YTD.")
# This initiates an automated chat between the two agents to solve the task
```

This example can be run with

```python
python test/twoagent.py
```

After the repo is cloned.
The figure below shows an example conversation flow with AutoGen.
![Agent Chat Example](https://github.com/microsoft/autogen/blob/main/website/static/img/chat_example.png)

Please find more [code examples](https://microsoft.github.io/autogen/docs/Examples/AutoGen-AgentChat) for this feature.

## Enhanced LLM Inferences

Autogen also helps maximize the utility out of the expensive LLMs such as ChatGPT and GPT-4. It offers a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` adding powerful functionalities like tuning, caching, error handling, and templating. For example, you can optimize generations by LLM with your own tuning data, success metrics, and budgets.

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

Please find more [code examples](https://microsoft.github.io/autogen/docs/Examples/AutoGen-Inference) for this feature.

## Documentation

You can find detailed documentation about AutoGen [here](https://microsoft.github.io/autogen/).

In addition, you can find:

- [Research](https://microsoft.github.io/autogen/docs/Research) and [blogposts](https://microsoft.github.io/autogen/blog) around AutoGen.

- [Discord](https://discord.gg/pAbnFJrkgZ).

- [Contributing guide](https://microsoft.github.io/autogen/docs/Contribute).

## Citation

[AutoGen](https://arxiv.org/abs/2308.08155).

```
@inproceedings{wu2023autogen,
      title={AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework},
      author={Qingyun Wu and Gagan Bansal and Jieyu Zhang and Yiran Wu and Shaokun Zhang and Erkang Zhu and Beibin Li and Li Jiang and Xiaoyun Zhang and Chi Wang},
      year={2023},
      eprint={2308.08155},
      archivePrefix={arXiv},
      primaryClass={cs.AI}
}
```

[EcoOptiGen](https://arxiv.org/abs/2303.04673).

```
@inproceedings{wang2023EcoOptiGen,
    title={Cost-Effective Hyperparameter Optimization for Large Language Model Generation Inference},
    author={Chi Wang and Susan Xueqing Liu and Ahmed H. Awadallah},
    year={2023},
    booktitle={AutoML'23},
}
```

[MathChat](https://arxiv.org/abs/2306.01337).

```
@inproceedings{wu2023empirical,
    title={An Empirical Study on Challenging Math Problem Solving with GPT-4},
    author={Yiran Wu and Feiran Jia and Shaokun Zhang and Hangyu Li and Erkang Zhu and Yue Wang and Yin Tat Lee and Richard Peng and Qingyun Wu and Chi Wang},
    year={2023},
    booktitle={ArXiv preprint arXiv:2306.01337},
}
```

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

If you are new to GitHub [here](https://help.github.com/categories/collaborating-with-issues-and-pull-requests/) is a detailed help source on getting involved with development on GitHub.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information, see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

# Legal Notices

Microsoft and any contributors grant you a license to the Microsoft documentation and other content
in this repository under the [Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode),
see the [LICENSE](LICENSE) file, and grant you a license to any code in the repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE-CODE](LICENSE-CODE) file.

Microsoft, Windows, Microsoft Azure, and/or other Microsoft products and services referenced in the documentation
may be either trademarks or registered trademarks of Microsoft in the United States and/or other countries.
The licenses for this project do not grant you rights to use any Microsoft names, logos, or trademarks.
Microsoft's general trademark guidelines can be found at http://go.microsoft.com/fwlink/?LinkID=254653.

Privacy information can be found at https://privacy.microsoft.com/en-us/

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel, or otherwise.
