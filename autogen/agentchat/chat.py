import logging
from typing import Dict, List, Any
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


def initiate_chats(chat_queue: List[Dict[str, Any]]) -> List[ChatResult]:
    """Initiate a list of chats.

    args:
        chat_queue (List[Dict]): a list of dictionaries containing the information of the chats.
                Each dictionary should contain the input arguments for `ConversableAgent.initiate_chat`.
                More specifically, each dictionary could include the following fields:
                recipient: the recipient agent.
                - "sender": the sender agent.
                - "recipient": the recipient agent.
                - clear_history (bool): whether to clear the chat history with the agent. Default is True.
                - silent (bool or None): (Experimental) whether to print the messages for this conversation. Default is False.
                - cache (Cache or None): the cache client to be used for this conversation. Default is None.
                - max_turns (int or None): the maximum number of turns for the chat. If None, the chat will continue until a termination condition is met. Default is None.
                - "message" needs to be provided if the `generate_init_message` method is not overridden.
                        Otherwise, input() will be called to get the initial message.
                - "summary_method": a string or callable specifying the method to get a summary from the chat. Default is DEFAULT_summary_method, i.e., "last_msg".
                    - Supported string are "last_msg" and "reflection_with_llm":
                        when set "last_msg", it returns the last message of the dialog as the summary.
                        when set "reflection_with_llm", it returns a summary extracted using an llm client.
                        `llm_config` must be set in either the recipient or sender.
                        "reflection_with_llm" requires the llm_config to be set in either the sender or the recipient.
                    - A callable summary_method should take the recipient and sender agent in a chat as input and return a string of summary. E.g,
                    ```python
                    def my_summary_method(
                        sender: ConversableAgent,
                        recipient: ConversableAgent,
                    ):
                        return recipient.last_message(sender)["content"]
                    ```
                "summary_prompt" can be used to specify the prompt used to extract a summary when summary_method is "reflection_with_llm".
                    Default is None and the following default prompt will be used when "summary_method" is set to "reflection_with_llm":
                    "Identify and extract the final solution to the originally asked question based on the conversation."
                "carryover" can be used to specify the carryover information to be passed to this chat.
                    If provided, we will combine this carryover with the "message" content when generating the initial chat
                    message in `generate_init_message`.


    returns:
        (list): a list of ChatResult objects corresponding to the finished chats in the chat_queue.
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
    finished_chats = []
    while current_chat_queue:
        chat_info = current_chat_queue.pop(0)
        _chat_carryover = chat_info.get("carryover", [])
        if isinstance(_chat_carryover, str):
            _chat_carryover = [_chat_carryover]
        chat_info["carryover"] = _chat_carryover + [r.summary for r in finished_chats]
        if "message" not in chat_info:
            warnings.warn(
                "message is not provided in a chat_queue entry. input() will be called to get the initial message.",
                UserWarning,
            )
        chat_info["recipient"]
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
        finished_chats.append(chat_res)
    return finished_chats
