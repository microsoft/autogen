import json
import copy
from typing import Dict, List, Optional, Union
import logging
import autogen


EXAMPLE_STATE_SPACE = [
    {
        "name": "USER_REQUEST",
        "description": "The message shows the *user* requesting a task that needs to be completed",
        "valid_roles": ["user"],
    },
    {
        "name": "SUGGESTING-CODE",
        "description": "The assistant is suggesting code",
        "valid_roles": ["assistant"],
    },
    {
        "name": "CODE-EXECUTION",
        "description": "The user shared results of code execution, e.g., results, logs, error trace",
        "valid_roles": ["user"],
    },
    {
        "name": "TASK-COMPLETED",
        "description": "The message from either user or assistant indicates that provided task was completed or the goal was accomplished, e.g., this maybe indicated through successful code execution, TERMINATE messsages, etc",
        "valid_roles": ["user", "assistant"],
    },
    {
        "name": "EMPTY",
        "description": "The message is empty",
        "valid_roles": ["user"],
    },
]


def state_space_to_str(state_space: List[Dict[str, Union[str, List[str]]]], filter_by_role: str = None) -> str:
    """
    Converts a state space to a string.

    Args:
        state_space: A list of dictionaries representing the state space. Each dictionary should have 'name', 'description'.
        filter_by_role: A string representing the role to filter by.

    Returns:
        str: A string representation of the state space.
    """
    # get states that are valid for the given role
    if filter_by_role is not None:
        state_space = [state for state in state_space if filter_by_role in state["valid_roles"]]
    return "\n".join([f"{state['name']}: {state['description']}" for state in state_space])


def annotate_message(
    role: str, content: str, state_space: Dict[str, str], llm_config: Optional[Dict] = None
) -> List[str]:
    """
    Annotates a message by performing qualitative coding.

    Args:
        role (str): The role of the agent (user or assistant) sending the message.
        content (str): The content of the message.
        state_space (Dict[str, str]): A dictionary mapping codes to descriptions.
        llm_config (Optional[Dict], optional): Configuration for the OpenAIWrapper. Defaults to None.


    Returns:
        codes: A list of codes that apply to the message.
    """

    if state_space is None:
        state_space = EXAMPLE_STATE_SPACE

    state_space_str = state_space_to_str(state_space, filter_by_role=role)

    prompt = f"""Which of the following codes apply to the message:

List of codes:
{state_space_str}

Message
    role: "{role}"
    content: "{content}"

Only respond with codes that apply. Codes should be separated by commas.
"""
    logging.debug(prompt)
    if llm_config is not None:
        client = autogen.OpenAIWrapper(**llm_config)
    else:
        client = autogen.OpenAIWrapper()
    response = client.create(cache_seed=None, messages=[{"role": "user", "content": prompt}])
    response = client.extract_text_or_completion_object(response)[0]
    return [code.strip() for code in response.split(",")]


def annotate_chat_history(
    chat_history: List[Dict[str, str]],
    state_space: Dict[str, str] = None,
    llm_config: Dict[str, str] = None,
    collate_codes: bool = False,
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
        role = message.get("name") if "name" in message else message.get("role")
        content = message.get("content")
        codes = annotate_message(role, content, llm_config=llm_config, state_space=state_space)
        if collate_codes is True:
            # sort the codes alphabetically
            codes = sorted(codes)
            codes = [", ".join(codes)]

        message["codes"] = codes

    return chat_history_annotated
