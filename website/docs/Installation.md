# Installation

## Setup Virtual Environment

When not using a docker container, we recommend using a virtual environment to install AutoGen. This will ensure that the dependencies for AutoGen are isolated from the rest of your system.

### Option 1: venv

You can create a virtual environment with `venv` as below:
```bash
python3 -m venv autogen
source autogen/bin/activate
```

### Option 2: conda

Another option is with `Conda`, Conda works better at solving dependency conflicts than pip. You can install it by following [this doc](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html),
and then create a virtual environment as below:
```bash
conda create -n autogen python=3.10  # python 3.10 is recommended as it's stable and not too old
conda activate autogen
```

Now, you're ready to install AutoGen in the virtual environment you've just created.

## Python

AutoGen requires **Python version >= 3.8**. It can be installed from pip:

```bash
pip install pyautogen
```

`pyautogen<0.2` requires `openai<1`. Starting from pyautogen v0.2, `openai>=1` is required.

<!--
or conda:
```
conda install pyautogen -c conda-forge
``` -->

### Optional Dependencies
* docker

For the best user experience and seamless code execution, we highly recommend using Docker with AutoGen. Docker is a containerization platform that simplifies the setup and execution of your code. Developing in a docker container, such as GitHub Codespace, also makes the development convenient.

When running AutoGen out of a docker container, to use docker for code execution, you also need to install the python package `docker`:
```bash
pip install docker
```

* blendsearch

AutoGen offers a cost-effective hyperparameter optimization technique [EcoOptiGen](https://arxiv.org/abs/2303.04673) for tuning Large Language Models. Please install with the [blendsearch] option to use it.
```bash
pip install "pyautogen[blendsearch]"
```

Example notebooks:
[Optimize for Code Generation](https://github.com/microsoft/autogen/blob/main/notebook/oai_completion.ipynb),
[Optimize for Math](https://github.com/microsoft/autogen/blob/main/notebook/oai_chatgpt_gpt4.ipynb)

* retrievechat

AutoGen supports retrieval-augmented generation tasks such as question answering and code generation with RAG agents. Please install with the [retrievechat] option to use it.
```bash
pip install "pyautogen[retrievechat]"
```

Example notebooks:
[Automated Code Generation and Question Answering with Retrieval Augmented Agents](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_RetrieveChat.ipynb),
[Group Chat with Retrieval Augmented Generation (with 5 group member agents and 1 manager agent)](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_groupchat_RAG.ipynb)

* mathchat

AutoGen offers an experimental agent for math problem solving. Please install with the [mathchat] option to use it.
```bash
pip install "pyautogen[mathchat]"
```

Example notebooks:
[Using MathChat to Solve Math Problems](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_MathChat.ipynb)
