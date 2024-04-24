import os
import autogen

from autogen.agentchat.contrib.orchestrator import Orchestrator
from autogen.agentchat.contrib.multimodal_web_surfer import MultimodalWebSurferAgent
from autogen.agentchat.contrib.mmagent import MultimodalAgent

from config_manager import ConfigManager
from misc_utils import response_preparer

# setup LLM config and clients

# config_list = "OAI_CONFIG_LIST"
# response_format_is_supported = True

config_list = "AZURE_OAI_CONFIG_LIST"
response_format_is_supported = False

config = ConfigManager()
config.initialize(config_path_or_env=config_list)

assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
    llm_config=config.mlm_config,
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
    llm_config=config.mlm_config,
    is_termination_msg=lambda x: str(x).find("TERMINATE") >= 0 or str(x).find("FINAL ANSWER") >= 0,
    human_input_mode="NEVER",
    headless=True,
    browser_channel="chromium",
    browser_data_dir=None,
    start_page="https://bing.com",
    debug_dir=os.path.join(os.path.dirname(__file__), "debug"),
)

maestro = Orchestrator(
    "orchestrator",
    agents=[assistant, computer_terminal, web_surfer],
    llm_config=config.mlm_config,
    response_format_is_supported=response_format_is_supported,
)

# # read the task from standard input
task = input("Enter the task: ")

computer_terminal.initiate_chat(maestro, message=task, clear_history=True)
