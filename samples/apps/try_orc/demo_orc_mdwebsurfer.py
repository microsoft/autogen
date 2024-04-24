import autogen
from autogen.agentchat.contrib.web_surfer import WebSurferAgent
from autogen.browser_utils import RequestsMarkdownBrowser, BingMarkdownSearch

from autogen.agentchat.contrib.orchestrator import Orchestrator

from config_manager import ConfigManager

# setup LLM config and clients
# config_list = "OAI_CONFIG_LIST"
config_list = "AZURE_OAI_CONFIG_LIST"

config = ConfigManager()
config.initialize(config_path_or_env=config_list)


assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
    llm_config=config.llm_config,
)

user_proxy_name = "computer_terminal"
user_proxy = autogen.UserProxyAgent(
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

browser = RequestsMarkdownBrowser(
    viewport_size=1024 * 5,
    downloads_folder="coding",
    search_engine=BingMarkdownSearch(bing_api_key=config.bing_api_key, interleave_results=False),
)

web_surfer = WebSurferAgent(
    "web_surfer",
    llm_config=config.llm_config,
    summarizer_llm_config=config.llm_config,
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config=False,
    browser=browser,
)

maestro = Orchestrator(
    "orchestrator",
    agents=[assistant, user_proxy, web_surfer],
    llm_config=config.llm_config,
)

# read the task from standard input
task = input("Enter the task: ")
user_proxy.initiate_chat(maestro, message=task, clear_history=True)
