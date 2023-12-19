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


def annotate_message(role: str, content: str, codes: str, llm_config: Optional[Dict] = None) -> str:
    """
    Annotates a message by performing qualitative coding.

    Args:
        role (str): The role of the agent (user or assistant) sending the message.
        content (str): The content of the message.
        llm_config (Optional[Dict], optional): Configuration for the OpenAIWrapper. Defaults to None.
        codes (List[str], optional): A prompt containing the codes of interest. Defaults to None.

    Returns:
        str: The extracted text or function call from the OpenAIWrapper response.
    """

    if codes is None:
        codes = EXAMPLE_CODES

    prompt = f"""You are a helpful assistant that is expert at qualitative analysis of text documents.

Given a message an agent (user or assistant), perform
qualitative coding with the following steps:
- Read the message to understand the context.
- Apply descriptive coding to categorize each message’s content. You must choose between the following
codes and respond with a comma separated list of unique codes:
{codes}

Be careful when you use codes. Do not confuse codes for user/assistant.

Message from *{role}*: {content}
 """

    if codes is not None:
        prompt = f"""Which of the following codes apply to the message:
codes: {codes}

role: {content}

Only respond with codes that apply. Codes should be separated by commas.
"""
    if llm_config is not None:
        client = autogen.OpenAIWrapper(**llm_config)
    else:
        client = autogen.OpenAIWrapper()

    response = client.create(cache_seed=None, messages=[{"role": "user", "content": prompt}])
    extracted_response = client.extract_text_or_completion_object(response)[0]
    if not isinstance(extracted_response, str):
        raise ValueError(str(extracted_response))
    else:
        return extracted_response


def annotate_chat_history(
    chat_history: List[Dict[str, str]],
    codes: str = None,
    llm_config: Dict[str, str] = None,
) -> List[Dict[str, str]]:
    """
    Annotates the chat history with codes based on the role and content of each message.

    Args:
        chat_history (List[Dict[str, str]]): A list of JSON objects representing the chat history. Each JSON object should have 'role' and 'content' keys.
        codes (List[str], optional): A prompt containing the codes of interest. Defaults to None.
        llm_config (Dict[str, str], optional): The configuration for the language model. Defaults to None.

    Returns:
        annotated_chat_history (List[Dict[str, str]]): A list of JSON objects representing the chat history. Each JSON object should have 'role', 'content', and 'codes' keys.
    """
    # Create a copy of the chat history object
    chat_history_annotated = copy.deepcopy(chat_history)

    for message in chat_history_annotated:
        role = message.get("role")
        content = message.get("content")
        message["codes"] = annotate_message(role, content, llm_config=llm_config, codes=codes)

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
