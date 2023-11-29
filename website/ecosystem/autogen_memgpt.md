---
slug: Autogen & MemGPT
title: Autogen & MemGPT
---
[Copied from MemGPT](https://memgpt.readthedocs.io/en/latest/autogen/)
## MemGPT + Autogen
[examples/agent_groupchat.py](https://github.com/cpacker/MemGPT/blob/main/memgpt/autogen/examples/agent_groupchat.py) contains an example of a groupchat where one of the agents is powered by MemGPT.

If you are using OpenAI, you can also run it using the [example notebook](https://github.com/cpacker/MemGPT/blob/main/memgpt/autogen/examples/memgpt_coder_autogen.ipynb).

In the next section, we detail how to set up MemGPT+Autogen to run with local LLMs.


## Connect Autogen + MemGPT to non-OpenAI LLMs (AutoGen+MemGPT+OpenLLMs)

In WebUI enable the [openai extension](https://github.com/oobabooga/text-generation-webui/tree/main/extensions/openai)! This is for non-MemGPT Autogen agents.

To get MemGPT to work with a local LLM, you need to have the LLM running on a server that takes API requests.

For the purposes of this example, we're going to serve (host) the LLMs using [oobabooga web UI](https://github.com/oobabooga/text-generation-webui#starting-the-web-ui), but if you want to use something else you can! This also assumes your running web UI locally - if you're running on e.g. Runpod, you'll want to follow Runpod specific instructions (for example use [TheBloke's one-click UI and API](https://github.com/TheBlokeAI/dockerLLM/blob/main/README_Runpod_LocalLLMsUIandAPI.md))

### Part 1: Get AutoGen working
1. Install oobabooga web UI using the instructions [here](https://github.com/oobabooga/text-generation-webui#starting-the-web-ui)
2. Once installed, launch the web server with `python server.py`
3. Navigate to the web app (if local, this is probably [`http://127.0.0.1:7860`](http://localhost:7860)), select the model you want to use, adjust your GPU and CPU memory settings, and click "load"
4. After the model is successfully loaded, navigate to the "Session" tab, and select and enable the "openai" extension. Then click "Apply flags/extensions and restart". The WebUI will then restart.
5. Once the WebUI has reloaded, double-check that your selected model and parameters are still selected -- If not, then select your model and re-apply your settings and click "load" once more.
5. Assuming steps 1-4 went correctly, the LLM is now properly hosted on a port you can point MemGPT to!

### Part 2: Get MemGPT working

1. In your terminal where you're running MemGPT (depending if you are on macOS or Windows), run either of the following:

***(Running WebUI locally)***

For macOS :
```sh
# the default port will be 5000
export OPENAI_API_BASE=http://127.0.0.1:5000
export BACKEND_TYPE=webui
```

For Windows (while using PowerShell & running WebUI locally):
```sh
$env:OPENAI_API_BASE = "http://127.0.0.1:5000"
$env:BACKEND_TYPE = "webui"
```

***(Running WebUI on Runpod)***

For macOS :
```sh
export OPENAI_API_BASE=https://yourpodaddresshere-5000.proxy.runpod.net
export BACKEND_TYPE=webui
```

For Windows (while using PowerShell):
```sh
$env:OPENAI_API_BASE = "https://yourpodaddresshere-5000.proxy.runpod.net"
$env:BACKEND_TYPE = "webui"
```

### Important Notes
- When exporting/setting the environment variables: Ensure that you do NOT include `/v1` as part of the address. MemGPT will automatically append the /v1 to the address.
    - For non-MemGPT Autogen agents: the [config](https://github.com/cpacker/MemGPT/blob/main/memgpt/autogen/examples/agent_groupchat.py#L38) should specify `/v1` in the address.

- Make sure you are using port 5000 (unless configured otherwise) when exporting the environment variables. MemGPT uses the non-OpenAI API, which is by default on port 5000 for WebUI.

- In the following steps, you will finish configuring Autogen to work with MemGPT+OpenLLMs. There is a `config_list` that will state to include `/v1` as part of the LocalHost address, as well as using port 5001 (instead of port 5000) which you must keep included (this is separate from the MemGPT `OPENAI_API_BASE` address you exported earlier, so AutoGen can connect to port 5001, which the "/v1" must remain).

WebUI exposes a lot of parameters that can dramatically change LLM outputs, to change these you can modify the [WebUI settings file](https://github.com/cpacker/MemGPT/blob/main/memgpt/local_llm/webui/settings.py).

⁉️ If you have problems getting WebUI setup, please use the [official web UI repo for support](https://github.com/oobabooga/text-generation-webui)! There will be more answered questions about web UI there vs here on the MemGPT repo.

### Example groupchat
Going back to the example we first mentioned, [examples/agent_groupchat.py](https://github.com/cpacker/MemGPT/blob/main/memgpt/autogen/examples/agent_groupchat.py) contains an example of a groupchat where one of the agents is powered by MemGPT.

In order to run this example on a local LLM, go to lines 32-55 in [examples/agent_groupchat.py](https://github.com/cpacker/MemGPT/blob/main/memgpt/autogen/examples/agent_groupchat.py) and fill in the config files with your local LLM's deployment details. For example, if you are using webui, it will look something like this:

```
config_list = [
    {
        "model": "dolphin-2.1-mistral-7b",  # this indicates the MODEL, not the WRAPPER (no concept of wrappers for AutoGen)
        "api_base": "http://127.0.0.1:5001/v1"
        "api_key": "NULL", # this is a placeholder
        "api_type": "open_ai",
    },
]
config_list_memgpt = [
    {
        "model": "airoboros-l2-70b-2.1",  # this specifies the WRAPPER MemGPT will use, not the MODEL
    },
]
```
`config_list` is used by non-MemGPT agents, which expect an OpenAI-compatible API.

`config_list_memgpt` is used by MemGPT agents. Currently, MemGPT interfaces with the LLM backend by exporting `OPENAI_API_BASE` and `BACKEND_TYPE` as described above. Note that MemGPT does not use the OpenAI-compatible API (it uses the direct API).

If you're using WebUI and want to run the non-MemGPT agents with a local LLM instead of OpenAI, enable the [openai extension](https://github.com/oobabooga/text-generation-webui/tree/main/extensions/openai) and point `config_list`'s `api_base` to the appropriate URL (usually port 5001).
Then, for MemGPT agents, export `OPENAI_API_BASE` and `BACKEND_TYPE` as described in [Local LLM support](../local_llm) (usually port 5000).


## Loading documents
[examples/agent_docs.py](https://github.com/cpacker/MemGPT/blob/main/memgpt/autogen/examples/agent_docs.py) contains an example of a groupchat where the MemGPT autogen agent has access to documents.

First, follow the instructions in [Example - chat with your data - Creating an external data source](../example_data/#creating-an-external-data-source):

To download the MemGPT research paper we'll use `curl` (you can also just download the PDF from your browser):
```sh
# we're saving the file as "memgpt_research_paper.pdf"
curl -L -o memgpt_research_paper.pdf https://arxiv.org/pdf/2310.08560.pdf
```

Now that we have the paper downloaded, we can create a MemGPT data source using `memgpt load`:
```sh
memgpt load directory --name memgpt_research_paper --input-files=memgpt_research_paper.pdf
```
```text
loading data
done loading data
LLM is explicitly disabled. Using MockLLM.
LLM is explicitly disabled. Using MockLLM.
Parsing documents into nodes: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 15/15 [00:00<00:00, 392.09it/s]
Generating embeddings: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 65/65 [00:01<00:00, 37.34it/s]
100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 65/65 [00:00<00:00, 388361.48it/s]
Saved local /home/user/.memgpt/archival/memgpt_research_paper/nodes.pkl
```

Note: you can ignore the "_LLM is explicitly disabled_" message.

Now, you can run `agent_docs.py`, which asks `MemGPT_coder` what a virtual context is:
```
❯ python3 agent_docs.py
LLM is explicitly disabled. Using MockLLM.
LLM is explicitly disabled. Using MockLLM.
LLM is explicitly disabled. Using MockLLM.
Generating embeddings: 0it [00:00, ?it/s]
new size 60
Saved local /Users/vivian/.memgpt/agents/agent_25/persistence_manager/index/nodes.pkl
Attached data source memgpt_research_paper to agent agent_25, consisting of 60. Agent now has 60 embeddings in archival memory.
LLM is explicitly disabled. Using MockLLM.
User_proxy (to chat_manager):

Tell me what a virtual context in MemGPT is. Search your archival memory.

--------------------------------------------------------------------------------
GroupChat is underpopulated with 2 agents. Direct communication would be more efficient.

MemGPT_coder (to chat_manager):

Virtual context management is a technique used in large language models like MemGPT. It's used to handle context beyond limited context windows, which is crucial for tasks such as extended conversations and document analysis. The technique was inspired by hierarchical memory systems in traditional operating systems that provide the appearance of large memory resources through data movement between fast and slow memory. This system intelligently manages different memory tiers to effectively provide extended context within the model's limited context window.

--------------------------------------------------------------------------------
...
```
