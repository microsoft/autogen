# AutoGen's Gradio GUI

This is a GUI for AutoGen. It is written in Python and uses the [Gradio](https://gradio.app/) library.

## Installation

First install AutoGen:

```bash
python -m pip install pyautogen
```

Next, run following command launch GUI:

```bash
export API_KEY=<your-api-key>
export API_KEY=<your-api-key>
python -m autogen.launch_gui
```

> Note:
> When you run `launch_gui`, the program will automatically install additional dependencies with `pip install --user ...`
>

## Customize your own multiagent chat


- Create a python file with templete below
- Edit and add your own multiagent chat
- Then run it

```python
# <-------------------  import  ------------------->
from autogen.gradio_gui.gradio_service import main, install_dependencies
from autogen.gradio_gui.plugin import autogen_terminal
from autogen.gradio_gui.utils.general import AutoGenGeneral, AutoGenGroupChat
from void_terminal.toolbox import CatchException

# <-------------------  define autogen agents (assistant + user_proxy) ------------------->
class AutoGenAskHuman(AutoGenGeneral):
    def define_agents(self):
        from autogen import AssistantAgent, UserProxyAgent
        return [
            {
                "name": "assistant",            # name of the agent.
                "cls":  AssistantAgent,         # class of the agent.
            },
            {
                "name": "user_proxy",           # name of the agent.
                "cls":  UserProxyAgent,         # class of the agent.
                "human_input_mode": "ALWAYS",   # always ask for human input.
                "llm_config": False,            # disables llm-based auto reply.
            },
        ]


# <-------------------  define autogen agents (group chat)  ------------------->
class AutoGenGroupChat(AutoGenGroupChat):
    def define_agents(self):
        from autogen import AssistantAgent, UserProxyAgent
        return [
            {
                "name": "Engineer",             # name of the agent.
                "cls":  AssistantAgent,         # class of the agent.
                "system_message": '''Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.                    Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.                     If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.'''
            },
            {
                "name": "Scientist",            # name of the agent.
                "cls":  AssistantAgent,         # class of the agent.
                "system_message": '''Scientist. You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code.'''
            },
            {
                "name": "Planner",              # name of the agent.
                "cls":  AssistantAgent,         # class of the agent.
                "system_message": '''Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. The plan may involve an engineer who can write code and a scientist who doesn't write code. Explain the plan first. Be clear which step is performed by an engineer, and which step is performed by a scientist.'''
            },
            {
                "name": "Executor",             # name of the agent.
                "cls":  UserProxyAgent,         # class of the agent.
                "human_input_mode": "NEVER",
                "system_message": '''Executor. Execute the code written by the engineer and report the result.'''
            },
            {
                "name": "Critic",               # name of the agent.
                "cls":  AssistantAgent,         # class of the agent.
                "system_message": '''Critic. Double check plan, claims, code from other agents and provide feedback. Check whether the plan includes adding verifiable info such as source URL.'''
            },
            {
                "name": "user_proxy",           # name of the agent.
                "cls":  UserProxyAgent,         # class of the agent.
                "human_input_mode": "NEVER",    # never ask for human input.
                "llm_config": False,            # disables llm-based auto reply.
                "code_execution_config": False,
                "system_message": "A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin.",
            },
        ]
    



# <-------------------  define autogen buttons  ------------------->
@CatchException
def autogen_terminal_fn_01(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenAskHuman, Callback="launch_gui->autogen_terminal_fn_01", **kwargs)

@CatchException
def autogen_terminal_fn_02(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenGroupChat, Callback="launch_gui->autogen_terminal_fn_02", **kwargs)


if __name__ == "__main__":
    # <-------------------  change configurations  ------------------->
    import void_terminal
    
    # void_terminal.set_conf(key="USE_PROXY", value=True)
    # void_terminal.set_conf(key="proxies", value='{"http": "http://localhost:10881", "https": "http://localhost:10881"}')
    void_terminal.set_conf(key="API_KEY",value="sk-yourapikey")
    void_terminal.set_conf(key="LLM_MODEL", value="gpt-3.5-turbo-16k")
    void_terminal.set_conf(key="AUTOGEN_USE_DOCKER", value=False)
    void_terminal.set_conf(key="PATH_LOGGING", value="gpt_log")
    void_terminal.set_conf(key="DARK_MODE", value=True)
    void_terminal.set_conf(key="AUTO_CLEAR_TXT", value=True)


    # <-------------------  add fn buttons to GUI & launch gradio  ------------------->
    from void_terminal.crazy_functions.ConversationHistoryArchive import ConversationHistoryArchive
    from void_terminal.crazy_functions.Accessibility import ClearCache
    main(
        {
            # <-------------------  autogen functions we defined above  ------------------->
            "AutoGen assitant": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_fn_01
            },
            "AutoGen sci group chat": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_fn_02
            },

            # <-------------------  other functions from void terminal  ------------------->
            "Save the current conversation": {
                "Group": "Conversation",
                "Color": "stop",
                "AsButton": True,
                "Info": "Save current conversation | No input parameters required",
                "AdvancedArgs": False,
                "Function": ConversationHistoryArchive
            },
            "Clear all cache files": {
                "Group": "Conversation",
                "Color": "stop",
                "AsButton": True,
                "Info": "Clear all cache files，Handle with caution | No input parameters required",
                "AdvancedArgs": False,
                "Function": ClearCache
            },
        }
    )

```

