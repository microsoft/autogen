from samples.apps.gradio_gui import install_dependencies, init_config  # do not move this line

if install_dependencies():  # do not move this line
    llm_config = init_config()  # do not move this line
    from samples.apps.gradio_gui.general import AutoGenGeneral, AutoGenGroupChat
    from samples.apps.gradio_gui.plugin import autogen_terminal
    from samples.apps.gradio_gui.gradio_service import main
    from void_terminal.toolbox import CatchException


class AutoGenAskHuman(AutoGenGeneral):
    def define_agents(self):
        from autogen import AssistantAgent, UserProxyAgent

        agents = [
            {
                "name": "assistant",  # name of the agent.
                "cls": AssistantAgent,  # class of the agent.
                "llm_config": llm_config,
            },
            {
                "name": "user_proxy",  # name of the agent.
                "cls": UserProxyAgent,  # class of the agent.
                "human_input_mode": "ALWAYS",  # always ask for human input.
                # disables llm-based auto reply.
                "llm_config": False,
            },
        ]
        return agents


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
                "name": "Scientist",  # name of the agent.
                "cls": AssistantAgent,  # class of the agent.
                "llm_config": llm_config,
                "system_message": """Scientist. You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code.""",
            },
            {
                "name": "Planner",  # name of the agent.
                "cls": AssistantAgent,  # class of the agent.
                "llm_config": llm_config,
                "system_message": """Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval. The plan may involve an engineer who can write code and a scientist who doesn't write code. Explain the plan first. Be clear which step is performed by an engineer, and which step is performed by a scientist.""",
            },
            {
                "name": "Executor",  # name of the agent.
                "cls": UserProxyAgent,  # class of the agent.
                "human_input_mode": "NEVER",
                "llm_config": llm_config,
                "system_message": """Executor. Execute the code written by the engineer and report the result.""",
            },
            {
                "name": "Critic",  # name of the agent.
                "cls": AssistantAgent,  # class of the agent.
                "llm_config": llm_config,
                "system_message": """Critic. Double check plan, claims, code from other agents and provide feedback. Check whether the plan includes adding verifiable info such as source URL.""",
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


# <-------------------  define autogen buttons  ------------------->


@CatchException
def autogen_terminal_fn_01(*args, **kwargs):
    return autogen_terminal(
        *args, AutoGenFn=AutoGenAskHuman, Callback="samples.apps.launch_gradio_gui->autogen_terminal_fn_01", **kwargs
    )


@CatchException
def autogen_terminal_fn_02(*args, **kwargs):
    return autogen_terminal(
        *args, AutoGenFn=AutoGenGroupChat, Callback="samples.apps.launch_gradio_gui->autogen_terminal_fn_02", **kwargs
    )


if __name__ == "__main__":
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
                "Function": autogen_terminal_fn_01,
            },
            "AutoGen sci group chat": {
                "Group": "Agent",
                "Color": "stop",
                "AsButton": True,
                "AdvancedArgs": False,
                "Function": autogen_terminal_fn_02,
            },
            # <-------------------  other functions from void terminal  ------------------->
            "Save the current conversation": {
                "Group": "Conversation",
                "Color": "stop",
                "AsButton": True,
                "Info": "Save current conversation | No input parameters required",
                "AdvancedArgs": False,
                "Function": ConversationHistoryArchive,
            },
            "Clear all cache files": {
                "Group": "Conversation",
                "Color": "stop",
                "AsButton": True,
                "Info": "Clear all cache files，Handle with caution | No input parameters required",
                "AdvancedArgs": False,
                "Function": ClearCache,
            },
        }
    )
