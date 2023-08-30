

# Getting Started

<!-- ### Welcome to AutoGen, a library for enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework! -->

AutoGen is a framework that enables development of LLM applications using multiple agents that can converse with each other to solve task. AutoGen agents are customizable, conversable, and seamlessly allow human participation. They can operate in various modes that employ combinations of LLMs, human inputs, and tools. 

### Main Features

* AutoGen enables building next-gen LLM applications based on multi-agent conversations with minimal effort. It simplifies the orchestration, automation and optimization of a complex LLM workflow. It maximizes the performance of LLM models and augments their weakness.
* It supports diverse conversation patterns for complex workflows. With customizable and conversable agents, developers can use AutoGen to build a wide range of conversation patterns concerning conversation autonomy,
the number of agents, and agent conversation topology.
* It provides a collection of working systems with different complexities. These systems
span a wide range of applications from various domains and complexities. They demonstrate how
AutoGen can easily support different conversation patterns.

AutoGen is powered by collaborative [research studies](/docs/Research) from Microsoft, Penn State University, and University of Washington.

### Quickstart

Install AutoGen from pip: `pip install pyautogen`. Find more options in [Installation](/docs/Installation).


Autogen enables the next-gen GPT-X applications with a generic multi-agent conversation framework.
It offers customizable and conversable agents which integrate LLMs, tools and human.
By automating chat among multiple capable agents, one can easily make them collectively perform tasks autonomously or with human feedback, including tasks that require using tools via code. For example,
```python
from pyautogen import AssistantAgent, UserProxyAgent
assistant = AssistantAgent("assistant")
user_proxy = UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Show me the YTD gain of 10 largest technology companies as of today.")
# This initiates an automated chat between the two agents to solve the task
```

Autogen also helps maximize the utility out of the expensive LLMs such as ChatGPT and GPT-4. It offers a drop-in replacement of `openai.Completion` or `openai.ChatCompletion` with powerful functionalites like tuning, caching, error handling, templating. For example, you can optimize generations by LLM with your own tuning data, success metrics and budgets.
```python
# perform tuning
config, analysis = pyautogen.Completion.tune(
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

### Where to Go Next?

* Understand the use cases for [Autogen](/docs/Use-Cases/Autogen).
* Find code examples from [Examples](/docs/Examples).
* Learn about [research](/docs/Research) around AutoGen and check [blogposts](/blog).
* Chat on [Discord](TBD).

If you like our project, please give it a [star](https://github.com/microsoft/autogen/stargazers) on GitHub. If you are interested in contributing, please read [Contributor's Guide](/docs/Contribute).

<iframe src="https://ghbtns.com/github-btn.html?user=microsoft&amp;repo=autogen&amp;type=star&amp;count=true&amp;size=large" frameborder="0" scrolling="0" width="170" height="30" title="GitHub"></iframe>