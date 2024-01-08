# Installation

## Option 1: Install and Run AutoGen in Docker

[Docker](https://www.docker.com/) is a containerization platform that simplifies the setup and execution of your code. A properly built docker image could provide isolated and consistent environment to run your code securely across platforms. One option of using AutoGen is to install and run it in a docker container. You can do that in [Github codespace](https://codespaces.new/microsoft/autogen?quickstart=1) or follow the instructions below to do so.

#### Step 1. Install Docker.

Install docker following [this instruction](https://docs.docker.com/get-docker/).

For Mac users, alternatively you may choose to install [colima](https://smallsharpsoftwaretools.com/tutorials/use-colima-to-run-docker-containers-on-macos/) to run docker containers, if there is any issues with starting the docker daemon.

#### Step 2. Build a docker image

AutoGen provides [dockerfiles](https://github.com/microsoft/autogen/tree/main/samples/dockers/) that could be used to build docker images. Use the following command line to build a docker image named `autogen_img` (or other names you prefer) from one of the provided dockerfiles named `Dockerfile.base`:

```
docker build -f samples/dockers/Dockerfile.base -t autogen_img https://github.com/microsoft/autogen.git#main
```
which includes some common python libraries and essential dependencies of AutoGen, or build from `Dockerfile.full` which include additional dependencies for more advanced features of AutoGen with the following command line:

```
docker build -f samples/dockers/Dockerfile.full -t autogen_full_img https://github.com/microsoft/autogen.git
```
Once you build the docker image, you can use `docker images` to check whether it has been created successfully.

#### Step 3.  Run applications built with AutoGen from a docker image.

**Mount your code to the docker image and run your application from there:** Now suppose you have your application built with AutoGen in a main script named `twoagent.py` ([example](https://github.com/microsoft/autogen/blob/main/test/twoagent.py)) in a folder named `myapp`. With the command line below, you can mont your folder and run the application in docker.

```python
# Mount the local folder `myapp` into docker image and run the script named "twoagent.py" in the docker.
docker run -it -v `pwd`/myapp:/myapp autogen_img:latest python /myapp/main_twoagent.py
```

<!-- You may also run [AutoGen Studio](https://github.com/microsoft/autogen/tree/main/samples/apps/autogen-studio) (assuming that you have built a docker image named `autogen_full_img` with `Dockerfile.full` and you have set the environment variable `OPENAI_API_KEY` to your OpenAI API key) as below:

```
docker run -it -e OPENAI_API_KEY=$OPENAI_API_KEY -p 8081:8081 autogen_full_img:latest autogenra ui --host 0.0.0.0
```
Then open `http://localhost:8081/` in your browser to use AutoGen Studio. -->

## Option 2: Install AutoGen Locally Using Virtual Environment

When installing AutoGen locally, we recommend using a virtual environment for the installation. This will ensure that the dependencies for AutoGen are isolated from the rest of your system.

### Option a: venv

You can create a virtual environment with `venv` as below:
```bash
python3 -m venv pyautogen
source pyautogen/bin/activate
```

The following command will deactivate the current `venv` environment:
```bash
deactivate
```

### Option b: conda

Another option is with `Conda`. You can install it by following [this doc](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html),
and then create a virtual environment as below:
```bash
conda create -n pyautogen python=3.10  # python 3.10 is recommended as it's stable and not too old
conda activate pyautogen
```

The following command will deactivate the current `conda` environment:
```bash
conda deactivate
```

### Option c: poetry

Another option is with `poetry`, which is a dependency manager for Python.

[Poetry](https://python-poetry.org/docs/) is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you. Poetry offers a lockfile to ensure repeatable installs, and can build your project for distribution.

You can install it by following [this doc](https://python-poetry.org/docs/#installation),
and then create a virtual environment as below:
```bash
poetry init
poetry shell

poetry add pyautogen
```

The following command will deactivate the current `poetry` environment:
```bash
exit
```

Now, you're ready to install AutoGen in the virtual environment you've just created.

## Python

AutoGen requires **Python version >= 3.8, < 3.12**. It can be installed from pip:

```bash
pip install pyautogen
```

`pyautogen<0.2` requires `openai<1`. Starting from pyautogen v0.2, `openai>=1` is required.

<!--
or conda:
```
conda install pyautogen -c conda-forge
``` -->

### Migration guide to v0.2

openai v1 is a total rewrite of the library with many breaking changes. For example, the inference requires instantiating a client, instead of using a global class method.
Therefore, some changes are required for users of `pyautogen<0.2`.

- `api_base` -> `base_url`, `request_timeout` -> `timeout` in `llm_config` and `config_list`. `max_retry_period` and `retry_wait_time` are deprecated. `max_retries` can be set for each client.
- MathChat is unsupported until it is tested in future release.
- `autogen.Completion` and `autogen.ChatCompletion` are deprecated. The essential functionalities are moved to `autogen.OpenAIWrapper`:
```python
from autogen import OpenAIWrapper
client = OpenAIWrapper(config_list=config_list)
response = client.create(messages=[{"role": "user", "content": "2+2="}])
print(client.extract_text_or_completion_object(response))
```
- Inference parameter tuning and inference logging features are currently unavailable in `OpenAIWrapper`. Logging will be added in a future release.
Inference parameter tuning can be done via [`flaml.tune`](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function).
- `seed` in autogen is renamed into `cache_seed` to accommodate the newly added `seed` param in openai chat completion api. `use_cache` is removed as a kwarg in `OpenAIWrapper.create()` for being automatically decided by `cache_seed`: int | None. The difference between autogen's `cache_seed` and openai's `seed` is that:
    * autogen uses local disk cache to guarantee the exactly same output is produced for the same input and when cache is hit, no openai api call will be made.
    * openai's `seed` is a best-effort deterministic sampling with no guarantee of determinism. When using openai's `seed` with `cache_seed` set to None, even for the same input, an openai api call will be made and there is no guarantee for getting exactly the same output.


### Optional Dependencies
- #### docker

Even if you install AutoGen locally, we highly recommend using Docker for [code execution](FAQ.md#enable-python-3-docker-image).

To use docker for code execution, you also need to install the python package `docker`:
```bash
pip install docker
```

You might want to override the default docker image used for code execution. To do that set `use_docker` key of `code_execution_config` property to the name of the image. E.g.:
```python
user_proxy = autogen.UserProxyAgent(
    name="agent",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir":"_output", "use_docker":"python:3"},
    llm_config=llm_config,
    system_message=""""Reply TERMINATE if the task has been solved at full satisfaction.
Otherwise, reply CONTINUE, or the reason why the task is not solved yet."""
)
```

- #### blendsearch

`pyautogen<0.2` offers a cost-effective hyperparameter optimization technique [EcoOptiGen](https://arxiv.org/abs/2303.04673) for tuning Large Language Models. Please install with the [blendsearch] option to use it.
```bash
pip install "pyautogen[blendsearch]<0.2"
```

Example notebooks:

[Optimize for Code Generation](https://github.com/microsoft/autogen/blob/main/notebook/oai_completion.ipynb)

[Optimize for Math](https://github.com/microsoft/autogen/blob/main/notebook/oai_chatgpt_gpt4.ipynb)

- #### retrievechat

`pyautogen` supports retrieval-augmented generation tasks such as question answering and code generation with RAG agents. Please install with the [retrievechat] option to use it.
```bash
pip install "pyautogen[retrievechat]"
```

RetrieveChat can handle various types of documents. By default, it can process
plain text and PDF files, including formats such as 'txt', 'json', 'csv', 'tsv',
'md', 'html', 'htm', 'rtf', 'rst', 'jsonl', 'log', 'xml', 'yaml', 'yml' and 'pdf'.
If you install [unstructured](https://unstructured-io.github.io/unstructured/installation/full_installation.html)
(`pip install "unstructured[all-docs]"`), additional document types such as 'docx',
'doc', 'odt', 'pptx', 'ppt', 'xlsx', 'eml', 'msg', 'epub' will also be supported.

You can find a list of all supported document types by using `autogen.retrieve_utils.TEXT_FORMATS`.

Example notebooks:

[Automated Code Generation and Question Answering with Retrieval Augmented Agents](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_RetrieveChat.ipynb)

[Group Chat with Retrieval Augmented Generation (with 5 group member agents and 1 manager agent)](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_groupchat_RAG.ipynb)

[Automated Code Generation and Question Answering with Qdrant based Retrieval Augmented Agents](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_qdrant_RetrieveChat.ipynb)


- #### Teachability

To use Teachability, please install AutoGen with the [teachable] option.
```bash
pip install "pyautogen[teachable]"
```

Example notebook:  [Chatting with a teachable agent](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_teachability.ipynb)



- #### Large Multimodal Model (LMM) Agents

We offered Multimodal Conversable Agent and LLaVA Agent. Please install with the [lmm] option to use it.
```bash
pip install "pyautogen[lmm]"
```

Example notebooks:

[LLaVA Agent](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_lmm_llava.ipynb)


- #### mathchat

`pyautogen<0.2` offers an experimental agent for math problem solving. Please install with the [mathchat] option to use it.
```bash
pip install "pyautogen[mathchat]<0.2"
```

Example notebooks:

[Using MathChat to Solve Math Problems](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_MathChat.ipynb)
