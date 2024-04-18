import os
import autogen

from autogen.agentchat.contrib.orchestrator import Orchestrator
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.agentchat.contrib.mmagent import MultimodalAgent

from config_manager import ConfigManager
from misc_utils import response_preparer

# setup LLM config and clients
config = ConfigManager()
config.initialize()

assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
    llm_config=config.llm_config,
)

user_proxy_name = "computer_terminal"
computer_terminal = autogen.UserProxyAgent(
    user_proxy_name,
    human_input_mode="NEVER",
    description="A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks)",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    default_auto_reply=f'Invalid {user_proxy_name} input: no code block detected.\nPlease provide {user_proxy_name} a complete Python script or a shell (sh) script to run. Scripts should appear in code blocks beginning "```python" or "```sh" respectively.',
    max_consecutive_auto_reply=15,
)


web_surfer = MultimodalWebSurferAgent(
    "web_surfer",
    llm_config=config.llm_config,
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0 or str(x).find("FINAL ANSWER") >= 0,
    human_input_mode="NEVER",
    headless=True,
    chromium_channel="chromium",
    chromium_data_dir=None,
    start_page="https://bing.com",
    debug_dir=os.path.join(os.path.dirname(__file__), "debug"),
)


mm_user_proxy = MultimodalAgent(
    "mm_user_proxy",
    system_message="""You are a general-purpose AI assistant and can handle many questions -- but you don't have access to a web browser. However, the user you are talking to does have a browser, and you can see the screen. Provide short direct instructions to them to take you where you need to go to answer the initial question posed to you.

Once the user has taken the final necessary action to complete the task, and you have fully addressed the initial request, reply with the word TERMINATE.""",
    description="A multimodal agent that can handle many questions but does not have access to a web browser. It can see the screen of the user it is talking to and can provide short direct instructions to the user to take them where they need to go to answer the initial question posed to them. Once the user has taken the final necessary action to complete the task, and the initial request has been fully addressed, the agent replies with the word TERMINATE.",
    llm_config=config.llm_config,
    human_input_mode="NEVER",
    is_termination_msg=lambda x: False,
    max_consecutive_auto_reply=20,
)


maestro = Orchestrator(
    "orchestrator",
    agents=[assistant, computer_terminal, web_surfer],
    llm_config=config.llm_config,
)

# # read the task from standard input
task = input("Enter the task: ")

computer_terminal.initiate_chat(maestro, message=task, clear_history=True)
