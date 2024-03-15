import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
import warnings
from termcolor import colored
from .utils import consolidate_chat_info


logger = logging.getLogger(__name__)
Prerequisite = Tuple[int, int]


@dataclass
class ChatResult:
    """(Experimental) The result of a chat. Almost certain to be changed."""

    chat_id: int = None
    """chat id"""
    chat_history: List[Dict[str, any]] = None
    """The chat history."""
    summary: str = None
    """A summary obtained from the chat."""
    cost: tuple = None  # (dict, dict) - (total_cost, actual_cost_with_cache)
    """The cost of the chat. a tuple of (total_cost, total_actual_cost), where total_cost is a dictionary of cost information, and total_actual_cost is a dictionary of information on the actual incurred cost with cache."""
    human_input: List[str] = None
    """A list of human input solicited during the chat."""


def _validate_recipients(chat_queue: List[Dict[str, Any]]) -> None:
    """
    Validate recipients exits and warn repetitive recipients.
    """
    receipts_set = set()
    for chat_info in chat_queue:
        assert "recipient" in chat_info, "recipient must be provided."
        receipts_set.add(chat_info["recipient"])
    if len(receipts_set) < len(chat_queue):
        warnings.warn(
            "Repetitive recipients detected: The chat history will be cleared by default if a recipient appears more than once. To retain the chat history, please set 'clear_history=False' in the configuration of the repeating agent.",
            UserWarning,
        )


def __create_async_prerequisites(chat_queue: List[Dict[str, Any]]) -> List[Prerequisite]:
    """
    Create list of Prerequisite (prerequisite_chat_id, chat_id)
    """
    prerequisites = []
    for chat_info in chat_queue:
        if "chat_id" not in chat_info:
            raise ValueError("Each chat must have a unique id for async multi-chat execution.")
        chat_id = chat_info["chat_id"]
        pre_chats = chat_info.get("prerequisites", [])
        for pre_chat_id in pre_chats:
            if not isinstance(pre_chat_id, int):
                raise ValueError("Prerequisite chat id is not int.")
            prerequisites.append((chat_id, pre_chat_id))
    return prerequisites


def __find_async_chat_order(chat_ids: Set[int], prerequisites: List[Prerequisite]) -> List[int]:
    """Find chat order for async execution based on the prerequisite chats

    args:
        num_chats: number of chats
        prerequisites: List of Prerequisite (prerequisite_chat_id, chat_id)

    returns:
        list: a list of chat_id in order.
    """
    edges = defaultdict(set)
    indegree = defaultdict(int)
    for pair in prerequisites:
        chat, pre = pair[0], pair[1]
        if chat not in edges[pre]:
            indegree[chat] += 1
            edges[pre].add(chat)
    bfs = [i for i in chat_ids if i not in indegree]
    chat_order = []
    steps = len(indegree)
    for _ in range(steps + 1):
        if not bfs:
            break
        chat_order.extend(bfs)
        nxt = []
        for node in bfs:
            if node in edges:
                for course in edges[node]:
                    indegree[course] -= 1
                    if indegree[course] == 0:
                        nxt.append(course)
                        indegree.pop(course)
                edges.pop(node)
        bfs = nxt

    if indegree:
        return []
    return chat_order


def __post_carryover_processing(chat_info: Dict[str, Any]):
    if "message" not in chat_info:
        warnings.warn(
            "message is not provided in a chat_queue entry. input() will be called to get the initial message.",
            UserWarning,
        )
    print_carryover = (
        ("\n").join([t for t in chat_info["carryover"]])
        if isinstance(chat_info["carryover"], list)
        else chat_info["carryover"]
    )
    message = chat_info.get("message")
    if isinstance(message, str):
        print_message = message
    elif callable(message):
        print_message = "Callable: " + message.__name__
    elif isinstance(message, dict):
        print_message = "Dict: " + str(message)
    elif message is None:
        print_message = "None"
    print(colored("\n" + "*" * 80, "blue"), flush=True, sep="")
    print(
        colored(
            "Starting a new chat....\n\nMessage:\n" + print_message + "\n\nCarryover: \n" + print_carryover,
            "blue",
        ),
        flush=True,
    )
    print(colored("\n" + "*" * 80, "blue"), flush=True, sep="")


def initiate_chats(chat_queue: List[Dict[str, Any]]) -> List[ChatResult]:
    """Initiate a list of chats.

    Args:
        chat_queue (List[Dict]): a list of dictionaries containing the information of the chats.
                Each dictionary should contain the input arguments for `ConversableAgent.initiate_chat`.
                More specifically, each dictionary could include the following fields:
                - "sender": the sender agent.
                - "recipient": the recipient agent.
                - "clear_history" (bool): whether to clear the chat history with the agent. Default is True.
                - "silent" (bool or None): (Experimental) whether to print the messages for this conversation. Default is False.
                - "cache" (Cache or None): the cache client to be used for this conversation. Default is None.
                - "max_turns" (int or None): the maximum number of turns for the chat. If None, the chat will continue until a termination condition is met. Default is None.
                - "summary_method" (str or callable): a string or callable specifying the method to get a summary from the chat. Default is DEFAULT_summary_method, i.e., "last_msg".
                - "summary_args" (dict): a dictionary of arguments to be passed to the summary_method. Default is {}.
                - "message" (str, callable or None): if None, input() will be called to get the initial message.
                - **context: additional context information to be passed to the chat.
                        - "carryover": It can be used to specify the carryover information to be passed to this chat.
                        If provided, we will combine this carryover with the "message" content when generating the initial chat
                            message in `generate_init_message`.

    Returns:
        (list): a list of ChatResult objects corresponding to the finished chats in the chat_queue.
    """

    consolidate_chat_info(chat_queue)
    _validate_recipients(chat_queue)
    current_chat_queue = chat_queue.copy()
    finished_chats = []
    while current_chat_queue:
        chat_info = current_chat_queue.pop(0)
        _chat_carryover = chat_info.get("carryover", [])
        if isinstance(_chat_carryover, str):
            _chat_carryover = [_chat_carryover]
        chat_info["carryover"] = _chat_carryover + [r.summary for r in finished_chats]
        __post_carryover_processing(chat_info)
        sender = chat_info["sender"]
        chat_res = sender.initiate_chat(**chat_info)
        finished_chats.append(chat_res)
    return finished_chats


async def a_initiate_chats(chat_queue: List[Dict[str, Any]]) -> Dict[int, ChatResult]:
    """(async) Initiate a list of chats.

    args:
        Please refer to `initiate_chats`.


    returns:
        (Dict): a dict of ChatId: ChatResult corresponding to the finished chats in the chat_queue.
    """

    consolidate_chat_info(chat_queue)
    _validate_recipients(chat_queue)
    chat_book = {chat_info["chat_id"]: chat_info for chat_info in chat_queue}
    num_chats = chat_book.keys()
    prerequisites = __create_async_prerequisites(chat_queue)
    chat_order_by_id = __find_async_chat_order(num_chats, prerequisites)
    finished_chats = dict()
    for chat_id in chat_order_by_id:
        chat_info = chat_book[chat_id]
        condition = asyncio.Condition()
        prerequisite_chat_ids = chat_info.get("prerequisites", [])
        async with condition:
            await condition.wait_for(lambda: all([id in finished_chats for id in prerequisite_chat_ids]))
            # Do the actual work here.
            _chat_carryover = chat_info.get("carryover", [])
            if isinstance(_chat_carryover, str):
                _chat_carryover = [_chat_carryover]
            chat_info["carryover"] = _chat_carryover + [
                finished_chats[pre_id].summary for pre_id in prerequisite_chat_ids
            ]
            __post_carryover_processing(chat_info)
            sender = chat_info["sender"]
            chat_res = await sender.a_initiate_chat(**chat_info)
            chat_res.chat_id = chat_id
            finished_chats[chat_id] = chat_res

    return finished_chats
