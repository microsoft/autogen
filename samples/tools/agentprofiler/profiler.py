import json
import copy
from typing import Dict, List, Optional
import autogen


EXAMPLE_CODES = """Available codes:
USER_REQUEST: The message shows the *user* requesting a task that needs to be completed
SUGGESTING-CODE: The assistant is suggesting code
CODE-EXECUTION: The user shared results of code execution, e.g., results, logs, error trace
TASK-COMPLETED: The message from either user or assistant indicates that provided task was
completed or the goal was accomplished, e.g., this maybe indicated through successful code
execution, TERMINATE messsages, etc"
"""

# maps codes to descriptions
# the keys define the label space
# and the descriptions define the label descriptions
EXAMPLE_STATE_SPACE = {
    "USER_REQUEST": "The message shows the *user* requesting a task that needs to be completed",
    "SUGGESTING-CODE": "The assistant is suggesting code",
    "CODE-EXECUTION": "The user shared results of code execution, e.g., results, logs, error trace",
    "TASK-COMPLETED": "The message from either user or assistant indicates that provided task was completed or the goal was accomplished, e.g., this maybe indicated through successful code execution, TERMINATE messsages, etc",
}


def state_space_to_str(state_space: Dict[str, str]) -> str:
    """
    Converts a state space to a string.

    Args:
        state_space (Dict[str, str]): A dictionary mapping codes to descriptions.

    Returns:
        str: A string representation of the state space.
    """
    return "\n".join([f"{k}: {v}" for k, v in state_space.items()])


def annotate_message(role: str, content: str, state_space: Dict[str, str], llm_config: Optional[Dict] = None) -> str:
    """
    Annotates a message by performing qualitative coding.

    Args:
        role (str): The role of the agent (user or assistant) sending the message.
        content (str): The content of the message.
        state_space (Dict[str, str]): A dictionary mapping codes to descriptions.
        llm_config (Optional[Dict], optional): Configuration for the OpenAIWrapper. Defaults to None.


    Returns:
        str: The extracted text or function call from the OpenAIWrapper response.
    """

    if state_space is None:
        state_space = EXAMPLE_STATE_SPACE

    state_space_str = state_space_to_str(state_space)

    prompt = f"""Which of the following codes apply to the message:
codes: {state_space_str}

role: {content}

Only respond with codes that apply. Codes should be separated by commas.
"""
    if llm_config is not None:
        client = autogen.OpenAIWrapper(**llm_config)
    else:
        client = autogen.OpenAIWrapper()

    response = client.create(cache_seed=None, messages=[{"role": "user", "content": prompt}])
    return client.extract_text_or_completion_object(response)


def annotate_chat_history(
    chat_history: List[Dict[str, str]],
    state_space: Dict[str, str] = None,
    llm_config: Dict[str, str] = None,
) -> List[Dict[str, str]]:
    """
    Annotates the chat history with codes based on the role and content of each message.

    Args:
        chat_history (List[Dict[str, str]]): A list of JSON objects representing the chat history. Each JSON object should have 'role' and 'content' keys.
        state_space (Dict[str, str], optional): A dictionary mapping codes to descriptions. Defaults to None.
        llm_config (Dict[str, str], optional): The configuration for the language model. Defaults to None.

    Returns:
        annotated_chat_history (List[Dict[str, str]]): A list of JSON objects representing the chat history. Each JSON object should have 'role', 'content', and 'codes' keys.
    """
    # Create a copy of the chat history object
    chat_history_annotated = copy.deepcopy(chat_history)

    for message in chat_history_annotated:
        role = message.get("role")
        content = message.get("content")
        message["codes"] = annotate_message(role, content, llm_config=llm_config, state_space=state_space)

    return chat_history_annotated


if __name__ == "__main__":
    chat_history = json.load(open("sample_data/chat_history.json"))

    llm_config = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={"model": ["gpt-4"]},
    )[0]

    labels = annotate_chat_history(chat_history, llm_config=llm_config)

    # Save the new JSON to disk
    with open("sample_data/chat_history_annotated.json", "w") as file:
        json.dump(labels, file, indent=2)
