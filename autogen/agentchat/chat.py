import logging
from typing import Dict, List
from dataclasses import dataclass
from .utils import consolidate_chat_info
import warnings

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    """(Experimental) The result of a chat. Almost certain to be changed."""

    chat_history: List[Dict[str, any]] = None
    """The chat history."""
    summary: str = None
    """A summary obtained from the chat."""
    cost: tuple = None  # (dict, dict) - (total_cost, actual_cost_with_cache)
    """The cost of the chat. a tuple of (total_cost, total_actual_cost), where total_cost is a dictionary of cost information, and total_actual_cost is a dictionary of information on the actual incurred cost with cache."""
    human_input: List[str] = None
    """A list of human input solicited during the chat."""


# returns a list of ChatResult
def initiate_chats(chat_queue) -> List[ChatResult]:
    """Initiate a list of chats.

    args:
        chat_queue: (list): A list of chat configurations. Each element is a dictionary with the following keys
            sender: (ConversableAgent): The sender of the chat.
            recipient: (ConversableAgent): The recipient of the chat.
            message: (str): The message to send.
            clear_history: (bool):  Whether to clear the chat history. Default to True.
            silent: (bool): Whether to print the chat history. Default to False.
            cache: (Cache): The cache to use. Default to None.
            summary_method: (str): The method to use to summarize the chat. Default to "last_msg".
            summary_prompt: (str): The prompt to use to summarize the chat.
            carryover: (list): A list of carryover messages. Default to None.
    """
    consolidate_chat_info(chat_queue)
    receipts_set = set()
    for chat_info in chat_queue:
        assert "recipient" in chat_info, "recipient must be provided."
        receipts_set.add(chat_info["recipient"])
    if len(receipts_set) < len(chat_queue):
        warnings.warn(
            "Repetitive recipients detected: The chat history will be cleared by default if a recipient appears more than once. To retain the chat history, please set 'clear_history=False' in the configuration of the repeating agent.",
            UserWarning,
        )
    current_chat_queue = chat_queue.copy()
    finished_chats = {}
    while current_chat_queue:
        chat_info = current_chat_queue.pop(0)
        _chat_carryover = chat_info.get("carryover", [])
        if isinstance(_chat_carryover, str):
            _chat_carryover = [_chat_carryover]
        chat_info["carryover"] = _chat_carryover + [r.summary for r in finished_chats.values()]
        if "message" not in chat_info:
            warnings.warn(
                "message is not provided in a chat_queue entry. input() will be called to get the initial message.",
                UserWarning,
            )
        current_agent = chat_info["recipient"]
        print_carryover = (
            ("\n").join([t for t in chat_info["carryover"]])
            if isinstance(chat_info["carryover"], list)
            else chat_info["carryover"]
        )
        print(colored("\n" + "*" * 80, "blue"), flush=True, sep="")
        print(
            colored(
                "Start a new chat with the following message: \n"
                + chat_info.get("message")
                + "\n\nWith the following carryover: \n"
                + print_carryover,
                "blue",
            ),
            flush=True,
        )
        print(colored("\n" + "*" * 80, "blue"), flush=True, sep="")
        sender = chat_info["sender"]
        chat_res = sender.initiate_chat(**chat_info)
        finished_chats[current_agent] = chat_res
    return finished_chats
