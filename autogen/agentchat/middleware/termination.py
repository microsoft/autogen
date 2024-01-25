from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Tuple, Union

from ...code_utils import content_str
from ...tty_utils import colored
from ..agent import Agent


class TerminationAndHumanReplyMiddleware:
    """A middleware that checks for termination and human reply.

    This middleware handles messages with OpenAI-compatible schema.

    Args:
        is_termination_msg (function): a function that takes a message in the form of a dictionary
            and returns a boolean value indicating if this received message is a termination message.
            The dict can contain the following keys: "content", "role", "name", "function_call".
        max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
            default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
            When set to 0, no auto reply will be generated.
        human_input_mode (str): whether to ask for human inputs every time a message is received.
            Possible values are "ALWAYS", "TERMINATE", "NEVER".
            (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                Under this mode, the conversation stops when the human input is "exit",
                or when is_termination_msg is True and there is no human input.
            (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                the number of auto reply reaches the max_consecutive_auto_reply.
            (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                when the number of auto reply reaches the max_consecutive_auto_reply or when is_termination_msg is True.
    """

    MAX_CONSECUTIVE_AUTO_REPLY = 100

    def __init__(
        self,
        is_termination_msg: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
    ):
        def _default_is_termination_msg(message: Dict[str, Any]) -> bool:
            return content_str(message.get("content")) == "TERMINATE"

        self._is_termination_msg: Callable[[Dict[str, Any]], bool] = (
            is_termination_msg if is_termination_msg is not None else _default_is_termination_msg
        )
        self._human_input_mode = human_input_mode
        self._max_consecutive_auto_reply = (
            max_consecutive_auto_reply if max_consecutive_auto_reply is not None else self.MAX_CONSECUTIVE_AUTO_REPLY
        )
        self._consecutive_auto_reply_counter: DefaultDict[Optional[Agent], int] = defaultdict(int)
        self._max_consecutive_auto_reply_dict: DefaultDict[Optional[Agent], int] = defaultdict(
            self.max_consecutive_auto_reply
        )

    def call(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        if messages is not None:
            message = messages[-1]
            final, reply = self._check_termination_and_human_reply(message, sender)
            if final:
                return reply
        return next(messages, sender)  # type: ignore [no-any-return, misc]

    async def a_call(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        if messages is not None:
            message = messages[-1]
            final, reply = await self._a_check_termination_and_human_reply(message, sender)
            if final:
                return reply
        return await next(messages, sender)  # type: ignore [no-any-return, misc]

    def max_consecutive_auto_reply(self, sender: Optional[Agent] = None) -> int:
        """The maximum number of consecutive auto replies."""
        return self._max_consecutive_auto_reply if sender is None else self._max_consecutive_auto_reply_dict[sender]

    def update_max_consecutive_auto_reply(self, value: int, sender: Optional[Agent] = None) -> None:
        """Update the maximum number of consecutive auto replies.

        Args:
            value (int): the maximum number of consecutive auto replies.
            sender (Agent): when the sender is provided, only update the max_consecutive_auto_reply for that sender.
        """
        if sender is None:
            self._max_consecutive_auto_reply = value
            for k in self._max_consecutive_auto_reply_dict:
                self._max_consecutive_auto_reply_dict[k] = value
        else:
            self._max_consecutive_auto_reply_dict[sender] = value

    def reset_consecutive_auto_reply_counter(self, sender: Optional[Agent] = None) -> None:
        """Reset the consecutive_auto_reply_counter of the sender."""
        if sender is None:
            self._consecutive_auto_reply_counter.clear()
        else:
            self._consecutive_auto_reply_counter[sender] = 0

    def _check_termination_and_human_reply(
        self,
        message: Dict[str, Any],
        sender: Optional[Agent] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if the conversation should be terminated, and if human reply is provided.

        This method checks for conditions that require the conversation to be terminated, such as reaching
        a maximum number of consecutive auto-replies or encountering a termination message. Additionally,
        it prompts for and processes human input based on the configured human input mode, which can be
        'ALWAYS', 'NEVER', or 'TERMINATE'. The method also manages the consecutive auto-reply counter
        for the conversation and prints relevant messages based on the human input received.

        Args:
            - messages (Optional[List[Dict]]): A list of message dictionaries, representing the conversation history.
            - sender (Optional[Agent]): The agent object representing the sender of the message.
            - config (Optional[Any]): Configuration object, defaults to the current instance if not provided.

        Returns:
            - Tuple[bool, Union[str, Dict, None]]: A tuple containing a boolean indicating if the conversation
            should be terminated, and a human reply which can be a string, a dictionary, or None.
        """
        reply = ""
        no_human_input_msg = ""
        if self._human_input_mode == "ALWAYS":
            reply = self._get_human_input(
                f"Provide feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "  # type: ignore [union-attr]
            )
            no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
            # if the human input is empty, and the message is a termination message, then we will terminate the conversation
            reply = reply if reply or not self._is_termination_msg(message) else "exit"
        else:
            if self._consecutive_auto_reply_counter[sender] >= self._max_consecutive_auto_reply_dict[sender]:
                if self._human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    terminate = self._is_termination_msg(message)
                    reply = self._get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "  # type: ignore [union-attr]
                        if terminate
                        else f"Please give feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "  # type: ignore [union-attr]
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply if reply or not terminate else "exit"
            elif self._is_termination_msg(message):
                if self._human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    reply = self._get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "  # type: ignore [union-attr]
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply or "exit"

        # print the no_human_input_msg
        if no_human_input_msg:
            print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

        # stop the conversation
        if reply == "exit":
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            return True, None

        # send the human reply
        if reply or self._max_consecutive_auto_reply_dict[sender] == 0:
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            # User provided a custom response, return function and tool failures indicating user interruption
            tool_returns = []
            if message.get("function_call", False):
                tool_returns.append(
                    {
                        "role": "function",
                        "name": message["function_call"].get("name", ""),
                        "content": "USER INTERRUPTED",
                    }
                )

            if message.get("tool_calls", False):
                tool_returns.extend(
                    [
                        {"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": "USER INTERRUPTED"}
                        for tool_call in message["tool_calls"]
                    ]
                )

            response: Dict[str, Any] = {"role": "user", "content": reply}
            if tool_returns:
                response["tool_responses"] = tool_returns

            return True, response

        # increment the consecutive_auto_reply_counter
        self._consecutive_auto_reply_counter[sender] += 1
        if self._human_input_mode != "NEVER":
            print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    async def _a_check_termination_and_human_reply(
        self,
        message: Dict[str, Any],
        sender: Optional[Agent] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """(async) Check if the conversation should be terminated, and if human reply is provided.

        This method checks for conditions that require the conversation to be terminated, such as reaching
        a maximum number of consecutive auto-replies or encountering a termination message. Additionally,
        it prompts for and processes human input based on the configured human input mode, which can be
        'ALWAYS', 'NEVER', or 'TERMINATE'. The method also manages the consecutive auto-reply counter
        for the conversation and prints relevant messages based on the human input received.

        Args:
            - messages (Optional[List[Dict]]): A list of message dictionaries, representing the conversation history.
            - sender (Optional[Agent]): The agent object representing the sender of the message.
            - config (Optional[Any]): Configuration object, defaults to the current instance if not provided.

        Returns:
            - Tuple[bool, Union[str, Dict, None]]: A tuple containing a boolean indicating if the conversation
            should be terminated, and a human reply which can be a string, a dictionary, or None.
        """
        reply = ""
        no_human_input_msg = ""
        if self._human_input_mode == "ALWAYS":
            reply = await self._a_get_human_input(
                f"Provide feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "  # type: ignore [union-attr]
            )
            no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
            # if the human input is empty, and the message is a termination message, then we will terminate the conversation
            reply = reply if reply or not self._is_termination_msg(message) else "exit"
        else:
            if self._consecutive_auto_reply_counter[sender] >= self._max_consecutive_auto_reply_dict[sender]:
                if self._human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    terminate = self._is_termination_msg(message)
                    reply = await self._a_get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "  # type: ignore [union-attr]
                        if terminate
                        else f"Please give feedback to {sender.name}. Press enter to skip and use auto-reply, or type 'exit' to stop the conversation: "  # type: ignore [union-attr]
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply if reply or not terminate else "exit"
            elif self._is_termination_msg(message):
                if self._human_input_mode == "NEVER":
                    reply = "exit"
                else:
                    # self.human_input_mode == "TERMINATE":
                    reply = await self._a_get_human_input(
                        f"Please give feedback to {sender.name}. Press enter or type 'exit' to stop the conversation: "  # type: ignore [union-attr]
                    )
                    no_human_input_msg = "NO HUMAN INPUT RECEIVED." if not reply else ""
                    # if the human input is empty, and the message is a termination message, then we will terminate the conversation
                    reply = reply or "exit"

        # print the no_human_input_msg
        if no_human_input_msg:
            print(colored(f"\n>>>>>>>> {no_human_input_msg}", "red"), flush=True)

        # stop the conversation
        if reply == "exit":
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            return True, None

        # send the human reply
        if reply or self._max_consecutive_auto_reply_dict[sender] == 0:
            # User provided a custom response, return function and tool results indicating user interruption
            # reset the consecutive_auto_reply_counter
            self._consecutive_auto_reply_counter[sender] = 0
            tool_returns = []
            if message.get("function_call", False):
                tool_returns.append(
                    {
                        "role": "function",
                        "name": message["function_call"].get("name", ""),
                        "content": "USER INTERRUPTED",
                    }
                )

            if message.get("tool_calls", False):
                tool_returns.extend(
                    [
                        {"role": "tool", "tool_call_id": tool_call.get("id", ""), "content": "USER INTERRUPTED"}
                        for tool_call in message["tool_calls"]
                    ]
                )

            response: Dict[str, Any] = {"role": "user", "content": reply}
            if tool_returns:
                response["tool_responses"] = tool_returns

            return True, response

        # increment the consecutive_auto_reply_counter
        self._consecutive_auto_reply_counter[sender] += 1
        if self._human_input_mode != "NEVER":
            print(colored("\n>>>>>>>> USING AUTO REPLY...", "red"), flush=True)

        return False, None

    def _get_human_input(self, prompt: str) -> str:
        """Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        reply = input(prompt)
        return reply

    async def _a_get_human_input(self, prompt: str) -> str:
        """(Async) Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        reply = input(prompt)
        return reply
