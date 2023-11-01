# AutoGen's Gradio GUI

This is a GUI for AutoGen. It is written in Python and uses the [Gradio](https://gradio.app/) library.

## Installation

1. install AutoGen:

```bash
python -m pip install pyautogen
```

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
# use `set` instead of `export` on Windows
export OAI_CONFIG_LIST='/path/to/OAI_CONFIG_LIST'
export AUTOGEN_USE_DOCKER='False'
export WEB_PORT=12345
# for more environment variables options, please refer to the void terminal project

python -m autogen.launch_gui
```

> Note:
> When you run `launch_gui`, the program will automatically install additional dependencies with `pip install --user ...` if they are not installed.

## Customize your own multiagent chat


- Create a python file with templete below
- Edit and add your own multiagent chat
- Then run it

```python

```

