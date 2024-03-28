# AutoGen's Gradio GUI

This is a GUI for AutoGen. It is written in Python and uses the [Gradio](https://gradio.app/) library.

## ⭐Installation

1. Install AutoGen:

```bash
python -m pip install pyautogen[gui]
```

## ⭐Run

1. Create a file named `OAI_CONFIG_LIST`, input your OpenAI or Azure OpenAI API key(s). For example:

    ```
    [
        {
            "model": "gpt-3.5-turbo-16k",
            "api_key": "----------------------------------",
            "api_type": "azure",
            "api_version": "2023-07-01-preview",
            "base_url": "https://your_deploy_url.openai.azure.com/openai/deployments/your_deploy_name/chat/completions?api-version=2023-05-15",
        }
    ]
    ```

2. Run following commands to launch the GUI:

    - Linux
        ```bash
        # export OAI_CONFIG_LIST='/path/to/OAI_CONFIG_LIST'
        export OAI_CONFIG_LIST='./OAI_CONFIG_LIST'
        export AUTOGEN_USE_DOCKER='False'
        export PATH_LOGGING='logs'
        export WEB_PORT=12345
        # for more environment variables options, please refer to the void terminal project

        python -m samples.apps.launch_gradio_gui
        ```

    - Windows CMD

        ```bash
        # set OAI_CONFIG_LIST=/path/to/OAI_CONFIG_LIST
        set OAI_CONFIG_LIST=./OAI_CONFIG_LIST
        set AUTOGEN_USE_DOCKER=False
        set PATH_LOGGING=logs
        set WEB_PORT=12345
        # for more environment variables options, please refer to the void terminal project

        python -m samples.apps.launch_gradio_gui
        ```


> Note:
> When you run `launch_gradio_gui`, the program will automatically install additional dependencies with `pip install --user ...` if they are not installed.

## ⭐Customization


1. Create a python file `test.py` with templete below
2. Edit and add your own group chat
3. Run it with `python test.py`

    ```python

    from samples.apps.gradio_gui import init_config  # do not remove this line.
    llm_config = init_config()                      # do not remove this line.
    from samples.apps.gradio_gui.general import AutoGenGroupChat
    from samples.apps.gradio_gui.plugin import autogen_terminal
    from samples.apps.gradio_gui.gradio_service import main
    import os

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
