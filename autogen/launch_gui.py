# <------------------- install dependencies  ------------------->
def try_install_deps(deps, reload_m=[]):
    """
    install dependencies if not installed.
    """
    input(f'You are about to install dependencies {str(deps)}, press Enter to continue ...')
    import subprocess, sys, importlib
    for dep in deps:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', dep])
    import site
    importlib.reload(site)
    for m in reload_m:
        importlib.reload(__import__(m))

# <-------------------  dependencies  ------------------->
try:
    import gradio as gr
    import void_terminal
except:
    try_install_deps(deps=["void-terminal>=0.0.8"]) 
    try_install_deps(deps=["https://github.com/binary-husky/gpt_academic/raw/master/docs/gradio-3.32.6-py3-none-any.whl"])

if gr.__version__ not in ['3.32.6']: 
    # this is a special version of gradio, which is not available on pypi.org
    try_install_deps(deps=["https://github.com/binary-husky/gpt_academic/raw/master/docs/gradio-3.32.6-py3-none-any.whl"])



# <-------------------  import  ------------------->
import void_terminal
from gradio_gui.gradio_service import main
from gradio_gui.plugin import autogen_terminal
from gradio_gui.utils.general import AutoGenGeneral
from void_terminal.toolbox import CatchException



# <-------------------  define autogen agents  ------------------->
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
class AutoGenGroupChat(AutoGenGeneral):
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
                "name": "Critic",              # name of the agent.
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
    
    def do_audogen(self, input):
        # ⭐⭐ run in subprocess
        import autogen
        from void_terminal.toolbox import trimmed_format_exc, ProxyNetworkActivate
        from gradio_gui.utils.pipe import PluginMultiprocessManager, PipeCom
        input = input.content
        with ProxyNetworkActivate("AutoGen"):
            config_list = [{
                'model': self.llm_kwargs['llm_model'], 
                'api_key': self.llm_kwargs['api_key'],
            },]
            code_execution_config={"work_dir": self.autogen_work_dir, "use_docker":self.use_docker}
            agents = self.define_agents()
            agents = []
            for agent_kwargs in agents:
                agent_cls = agent_kwargs.pop('cls')
                kwargs = {
                    'llm_config':{
                        "config_list": config_list,
                    },
                    'code_execution_config':code_execution_config
                }
                kwargs.update(agent_kwargs)
                agent_handle = agent_cls(**kwargs)
                agent_handle._print_received_message = lambda a,b: self.gpt_academic_print_override(agent_kwargs, a, b)
                agents.append(agent_handle)
                if agent_kwargs['name'] == 'user_proxy':
                    agent_handle.get_human_input = lambda a: self.gpt_academic_get_human_input(user_proxy, a)
                    user_proxy = agent_handle
            try:
                groupchat = autogen.GroupChat(agents=agents, messages=[], max_round=50)
                manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={
                    "temperature": 0,
                    "config_list": config_list,
                })
                if user_proxy is None: raise Exception("user_proxy is not defined")
                user_proxy.initiate_chat(manager, message=input)
            except Exception as e:
                tb_str = '```\n' + trimmed_format_exc() + '```'
                self.child_conn.send(PipeCom("done", "AutoGen exe failed: \n\n" + tb_str))


# <-------------------  define autogen buttons  ------------------->
@CatchException
def autogen_terminal_fn_01(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenAskHuman, Callback="launch_gui->autogen_terminal_fn_01", **kwargs)

@CatchException
def autogen_terminal_fn_02(*args, **kwargs):
    return autogen_terminal(*args, AutoGenFn=AutoGenAskHuman, Callback="launch_gui->autogen_terminal_fn_02", **kwargs)


if __name__ == "__main__":
    # <-------------------  change configurations  ------------------->

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

            # <-------------------  other functions from void terminal  ------------------->
            "Save the current conversation": {
                "Group": "Conversation",
                "Color": "stop",
                "AsButton": True,
                "Info": "Save current conversation | No input parameters required",
                "AdvancedArgs": False,
                "Function": ConversationHistoryArchive
            },
            "Clear all cache files（Handle with caution）": {
                "Group": "Conversation",
                "Color": "stop",
                "AsButton": True,
                "Info": "Clear all cache files，Handle with caution | No input parameters required",
                "AdvancedArgs": False,
                "Function": ClearCache
            },
        }
    )
