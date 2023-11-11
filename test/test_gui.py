from samples.app.gradio_gui import init_config
from samples.app.gradio_gui.general import AutoGenGroupChat
from samples.app.gradio_gui.plugin import autogen_terminal
from samples.app.gradio_gui.gradio_service import main
import os

llm_config = init_config()


# <-------------------  define autogen agents (group chat)  ------------------->
class AutoGenGroupChat(AutoGenGroupChat):
    def define_agents(self):
        from autogen import AssistantAgent, UserProxyAgent

        agents = [
            {
                "name": "Engineer",  # name of the agent.
                "cls": AssistantAgent,  # class of the agent.
                "llm_config": llm_config,
                "system_message": """Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.                    Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.                     If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.""",
            },
            {
                "name": "user_proxy",  # name of the agent.
                "cls": UserProxyAgent,  # class of the agent.
                "human_input_mode": "NEVER",  # never ask for human input.
                # disables llm-based auto reply.
                "llm_config": False,
                "code_execution_config": False,
                "system_message": "A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin.",
            },
        ]
        return agents

    def define_group_chat_manager_config(self):
        llm_config.update({"temperature": 0})
        return {"llm_config": llm_config}


def autogen_terminal_groupchat(*args, **kwargs):
    return autogen_terminal(
        *args,
        AutoGenFn=AutoGenGroupChat,
        Callback=f"{os.path.basename(__file__).split('.py')[0]}->autogen_terminal_fn_02",
        **kwargs,
    )


if __name__ == "__main__":
    main(
        {
            "AutoGen sci group chat": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_groupchat,
            },
        }
    )
