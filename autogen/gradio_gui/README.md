# AutoGen's Gradio GUI

This is a GUI for AutoGen. It is written in Python and uses the [Gradio](https://gradio.app/) library.

## ⭐Installation

1. install AutoGen:

```bash
python -m pip install pyautogen
```

## ⭐Run

2. create `OAI_CONFIG_LIST`, write your OpenAI API key or azure API key. For example:

```
[
    {
        "model": "gpt-3.5-turbo-16k",
        "api_key": "----------------------------------",
        "api_base": "https://--------.openai.azure.com",
        "api_type": "azure",
        "api_version": "2023-07-01-preview",
        "deployment_id": "------"
    }
]

```

3. run following commands launch GUI:

```bash
export OAI_CONFIG_LIST='/path/to/OAI_CONFIG_LIST'
export AUTOGEN_USE_DOCKER='False'
export WEB_PORT=12345
# for more environment variables options, please refer to the void terminal project

python -m autogen.launch_gui
```

> Note:
> When you run `launch_gui`, the program will automatically install additional dependencies with `pip install --user ...` if they are not installed.

## ⭐Customize


1. Create a python file `test.py` with templete below
2. Edit and add your own multiagent chat
3. Run it with `python test.py`

```python

from autogen.gradio_gui import init_config
from autogen.gradio_gui.utils.general import AutoGenGroupChat
from autogen.gradio_gui.plugin import autogen_terminal
from autogen.gradio_gui.gradio_service import main
import os
llm_config = init_config()

# <-------------------  define autogen agents (group chat)  ------------------->
class AutoGenGroupChat(AutoGenGroupChat):
    def define_agents(self):
        from autogen import AssistantAgent, UserProxyAgent
        agents = [
            {
                "name": "Engineer",             # name of the agent.
                "cls":  AssistantAgent,         # class of the agent.
                "llm_config": llm_config,
                "system_message": "Engineer_Prompt."
            },
            {
                "name": "user_proxy",           # name of the agent.
                "cls":  UserProxyAgent,         # class of the agent.
                "human_input_mode": "NEVER",    # never ask for human input.
                # disables llm-based auto reply.
                "llm_config": False,
                "code_execution_config": False,
                "system_message": "A_Human_Admin.",
            },
        ]
        return agents

    def define_group_chat_manager_config(self):
        llm_config.update({"temperature": 0})
        return {"llm_config": llm_config}
    
def autogen_terminal_groupchat(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenGroupChat, Callback=f"{os.path.basename(__file__).split('.py')[0]}->autogen_terminal_fn_02", **kwargs)

if __name__ == "__main__":
    main(
        {
            "AutoGen sci group chat": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_groupchat
            },
        }
    )
```

