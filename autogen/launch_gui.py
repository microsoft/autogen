import void_terminal
from gradio_gui.gradio_service import main
from gradio_gui.plugin import autogen_terminal
from gradio_gui.utils.general import AutoGenGeneral
from void_terminal.crazy_functions.crazy_utils import try_install_deps
from void_terminal.toolbox import CatchException, HotReload

import gradio as gr
if gr.__version__ not in ['3.32.6']: 
    try_install_deps(deps=["https://github.com/binary-husky/gpt_academic/raw/master/docs/gradio-3.32.6-py3-none-any.whl"]) 
    # this is a special version of gradio, which is not available on pypi.org

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
    
class AutoGenNeverAsk(AutoGenGeneral):
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
                "human_input_mode": "NEVER",    # never ask for human input.
                "llm_config": False,            # disables llm-based auto reply.
            },
        ]

@CatchException
def autogen_terminal_fn_01(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenAskHuman, Callback="launch_gui->autogen_terminal_fn_01", **kwargs)

@CatchException
def autogen_terminal_fn_02(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenAskHuman, Callback="launch_gui->autogen_terminal_fn_02", **kwargs)


if __name__ == "__main__":
    # void_terminal.set_conf(key="USE_PROXY", value=True)
    # void_terminal.set_conf(key="proxies", value='{"http": "http://localhost:10881", "https": "http://localhost:10881"}')
    void_terminal.set_conf(key="API_KEY",value="sk-yourapikey")
    void_terminal.set_conf(key="LLM_MODEL", value="gpt-3.5-turbo-16k")
    void_terminal.set_conf(key="AUTOGEN_USE_DOCKER", value=False)
    void_terminal.set_conf(key="PATH_LOGGING", value="gpt_log")
    void_terminal.set_conf(key="DARK_MODE", value=True)
    void_terminal.set_conf(key="AUTO_CLEAR_TXT", value=True)

    main(
        {
            "AutoGen_Fn_01": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_fn_01
            },
            "AutoGen_Fn_02": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_fn_02
            },
        }
    )
