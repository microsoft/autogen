import logging
import sys
import types
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import re
from autogen import ConversableAgent
from abc import abstractmethod
logger = logging.getLogger(__name__)

try:
    from termcolor import colored
except ImportError:
    def colored(x, *args, **kwargs):
        return x
    

from autogen.code_utils import (
    UNKNOWN,
    content_str,
)
from autogen.oai.client import OpenAIWrapper


def in_n_th_msg(messages: List[Dict[str, str]], pattern: str, n: int = -1) -> bool:
    """Check if the pattern is in the n-th messages.
    Args:
        messages (list[dict]): a list of messages received from other agents.
            The messages are dictionaries that are JSON-serializable and
            follows the OpenAI's ChatCompletion schema.
        pattern (str): the pattern to search for
        n (int): the n-th message to search for. Default is the last message.
    """
    return pattern in messages[n]["content"]


def in_last_msg(messages: List[Dict[str, str]], pattern: str) -> bool:
    """Check if the pattern is in the last message.
    Args:
        messages (list[dict]): a list of messages received from other agents.
            The messages are dictionaries that are JSON-serializable and
            follows the OpenAI's ChatCompletion schema.
        pattern (str): the pattern to search for
    """
    return in_n_th_msg(messages, pattern, -1)


class StateFlow:
    states: Dict[str, List]
    final_states: List[str] = []
    initial_state: str = None
    transitions: Dict[str, Union[str, callable]] = {}

    messages: List[Dict[str, str]]
    current_state: str
    max_transitions: int = 10
    state_history: List[str] = []
    turn_count: int = 0
    verbose: bool = True

    use_name: bool = False # append name to a message if True

    def __init__(self):
        pass

    @abstractmethod
    def output_extraction(self, messages: List[Dict[str, str]]) -> str:
        """Extract the output from the messages."""
        return messages

    def check_states(self):
        """Check that the states are well defined."""
        assert self.initial_state is not None, "Initial state not defined"
        assert len(self.final_states) > 0, "No final states defined"
        assert self.initial_state in self.states, f"Initial state {self.initial_state} not defined in states"
        for state in self.final_states:
            assert state in self.states, f"Final state {state} not defined in states"

        for state in self.states:
            assert state in self.transitions, f"Transition for state {state} not defined"

    def reset(self):
        """Reset the state machine.
        Set state to initial state and clear the messages.
        Reset all agents or other stateful actions.
        """
        self.turn_count = 0
        self.current_state = self.initial_state
        self.messages = []
        self.state_history = []
        for s in self.states:
            for output_func in self.states[s]:
                if isinstance(output_func, ConversableAgent):
                    output_func.reset()

    def run(self, task: str, verbose: bool = True):
        self.reset()
        self.check_states()
        self.verbose = verbose

        self.messages.append({"content": task, "role": "user"})
        while self.current_state not in self.final_states:
            if self.verbose:
                print(colored(f"*********State {self.current_state}*********", "blue"), flush=True)
            
            # Run the output functions for the current state
            for output_func in self.states[self.current_state]:
                self.enter(output_func)
            
            # Transition to the next state
            if type(self.transitions[self.current_state]) is str:
                self.current_state = self.transitions[self.current_state]
            else:
                self.current_state = self.transitions[self.current_state](self.messages)

            self.state_history.append(self.current_state)
            if self.turn_count >= self.max_transitions:
                break
        return self.output_extraction(self.messages)

    def enter(self, output_func: Union[str, callable, dict]): 
        output_name = ""
        output_role = "user"
        if type(output_func) is types.FunctionType or type(output_func) is types.MethodType:
            result = output_func(self.messages)
        elif isinstance(output_func, ConversableAgent):
            result = output_func.generate_reply(self.messages)
            output_role = output_func._role
            output_name = output_func.name
        elif type(output_func) is dict:
            result = output_func
        elif type(output_func) is str:
            pass
        else: 
            raise ValueError(f"Invalid output function type: {type(output_func)}")
        
        if isinstance(result, str):
            result = {"content": result, "role": output_role}
        if self.use_name and output_name != "":
            result['name'] = output_name

        if isinstance(result, types.GeneratorType):
            # TODO: stream function_call / function_calls: update result
            pass
        else: 
            if self.verbose:
                self._print_received_message(result, name=output_name)

        self.messages.append(result)

    def _print_received_message(self, message: Union[Dict, str], name: str = "", inloop: bool = False):
        """Adapted from [`_print_received_message`](ConversableAgent#_print_received_message)"""
        if not inloop:
            if name == "":
                print(colored(f"Output {len(self.messages)}:", "yellow"), flush=True)
            else:
                print(colored(f"Output {len(self.messages)} ({name}):", "yellow"), flush=True) 

        if message.get("tool_responses"):  # Handle tool multi-call responses
            for tool_response in message["tool_responses"]:
                self._print_received_message(tool_response, inloop=True)
            if message.get("role") == "tool":
                return  # If role is tool, then content is just a concatenation of all tool_responses

        if message.get("role") in ["function", "tool"]:
            if message["role"] == "function":
                id_key = "name"
            else:
                id_key = "tool_call_id"

            func_print = f"***** Response from calling {message['role']} \"{message[id_key]}\" *****"
            print(colored(func_print, "green"), flush=True)
            print(message["content"], flush=True)
            print(colored("*" * len(func_print), "green"), flush=True)
        else:
            content = message.get("content")
            if content is not None:
                if "context" in message:
                    content = OpenAIWrapper.instantiate(
                        content,
                        message["context"],
                        self.llm_config and self.llm_config.get("allow_format_str_template", False),
                    )
                print(content_str(content), flush=True)
            if "function_call" in message and message["function_call"]:
                function_call = dict(message["function_call"])
                func_print = (
                    f"***** Suggested function Call: {function_call.get('name', '(No function name found)')} *****"
                )
                print(colored(func_print, "green"), flush=True)
                print(
                    "Arguments: \n",
                    function_call.get("arguments", "(No arguments found)"),
                    flush=True,
                    sep="",
                )
                print(colored("*" * len(func_print), "green"), flush=True)
            if "tool_calls" in message and message["tool_calls"]:
                for tool_call in message["tool_calls"]:
                    id = tool_call.get("id", "(No id found)")
                    function_call = dict(tool_call.get("function", {}))
                    func_print = f"***** Suggested tool Call ({id}): {function_call.get('name', '(No function name found)')} *****"
                    print(colored(func_print, "green"), flush=True)
                    print(
                        "Arguments: \n",
                        function_call.get("arguments", "(No arguments found)"),
                        flush=True,
                        sep="",
                    )
                    print(colored("*" * len(func_print), "green"), flush=True)

        print("\n", "-" * 80, flush=True, sep="")
