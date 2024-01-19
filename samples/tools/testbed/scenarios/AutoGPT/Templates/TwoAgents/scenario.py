from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
import testbed_utils

# Assistant agent can call check.py to check if all the unit tests have passed
testbed_utils.init()

work_dir = "coding"
target_folder = "__TARGET_FOLDER__"  # path to the artifact folder

config_list = config_list_from_json("OAI_CONFIG_LIST", filter_dict={"model": ["__MODEL__"]})

assistant = AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config={
        "config_list": config_list,
    },
)
user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": work_dir,
        "use_docker": False,
    },
    max_consecutive_auto_reply=5,
    # default_auto_reply="TERMINATE",
)

if target_folder:
    # The tasks involves reading from a file then do sth to it.
    message = """
    Here is the task description: __TASK__ The file you needed is located in this directory: '__TARGET_FOLDER__'. You should save the output files in the current directory: './'
    Run the following command to check if all the unit tests have passed:
    ```bash
    python ../check.py
    ```
    You should refine the code and results until all the tests have passed.
    """
else:
    message = """
    Here is the task description: __TASK__
    Run the following command to check if all the unit tests have passed:
    ```bash
    python ../check.py
    ```
    You should refine the code and results until all the tests have passed.
    """
user_proxy.initiate_chat(
    assistant,
    message=message,
)

testbed_utils.finalize(agents=[assistant, user_proxy])
