# ruff: noqa: E722
import copy
import traceback
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

from autogen import Agent, ConversableAgent, GroupChat, GroupChatManager, OpenAIWrapper


class SocietyOfMindAgent(ConversableAgent):
    """(In preview) A single agent that runs a Group Chat as an inner monologue.
    At the end of the conversation (termination for any reason), the SocietyOfMindAgent
    applies the response_preparer method on the entire inner monologue message history to
    extract a final answer for the reply.

    Most arguments are inherited from ConversableAgent. New arguments are:
        chat_manager (GroupChatManager): the group chat manager that will be running the inner monologue
        response_preparer (Optional, Callable or String): If response_preparer is a callable function, then
                it should have the signature:
                    f( self: SocietyOfMindAgent, messages: List[Dict])
                where `self` is this SocietyOfMindAgent, and `messages` is a list of inner-monologue messages.
                The function should return a string representing the final response (extracted or prepared)
                from that history.
                If response_preparer is a string, then it should be the LLM prompt used to extract the final
                message from the inner chat transcript.
                The default response_preparer depends on if an llm_config is provided. If llm_config is False,
                then the response_preparer deterministically returns the last message in the inner-monolgue. If
                llm_config is set to anything else, then a default LLM prompt is used.
    """

    def __init__(
        self,
        name: str,
        chat_manager: GroupChatManager,
        response_preparer: Optional[Union[str, Callable]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        **kwargs,
    ):
        super().__init__(
            name=name,
            system_message="",
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
            **kwargs,
        )

        self.update_chat_manager(chat_manager)

        # response_preparer default depends on if the llm_config is set, and if a client was created
        if response_preparer is None:
            if self.client is not None:
                response_preparer = "Output a standalone response to the original request, without mentioning any of the intermediate discussion."
            else:

                def response_preparer(agent, messages):
                    return messages[-1]["content"].replace("TERMINATE", "").strip()

        # Create the response_preparer callable, if given only a prompt string
        if isinstance(response_preparer, str):
            self.response_preparer = lambda agent, messages: agent._llm_response_preparer(response_preparer, messages)
        else:
            self.response_preparer = response_preparer

        # NOTE: Async reply functions are not yet supported with this contrib agent
        self._reply_func_list = []
        self.register_reply([Agent, None], SocietyOfMindAgent.generate_inner_monologue_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def _llm_response_preparer(self, prompt, messages):
        """Default response_preparer when provided with a string prompt, rather than a callable.

        Args:
            prompt (str): The prompt used to extract the final response from the transcript.
            messages (list): The messages generated as part of the inner monologue group chat.
        """

        _messages = [
            {
                "role": "system",
                "content": """Earlier you were asked to fulfill a request. You and your team worked diligently to address that request. Here is a transcript of that conversation:""",
            }
        ]

        for message in messages:
            message = copy.deepcopy(message)
            message["role"] = "user"

            # Convert tool and function calls to basic messages to avoid an error on the LLM call
            if "content" not in message:
                message["content"] = ""

            if "tool_calls" in message:
                del message["tool_calls"]
            if "tool_responses" in message:
                del message["tool_responses"]
            if "function_call" in message:
                if message["content"] == "":
                    try:
                        message["content"] = (
                            message["function_call"]["name"] + "(" + message["function_call"]["arguments"] + ")"
                        )
                    except KeyError:
                        pass
                    del message["function_call"]

            # Add the modified message to the transcript
            _messages.append(message)

        _messages.append(
            {
                "role": "system",
                "content": prompt,
            }
        )

        response = self.client.create(context=None, messages=_messages, cache=self.client_cache)
        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        if not isinstance(extracted_response, str):
            return str(extracted_response.model_dump(mode="dict"))
        else:
            return extracted_response

    @property
    def chat_manager(self) -> Union[GroupChatManager, None]:
        """Return the group chat manager."""
        return self._chat_manager

    def update_chat_manager(self, chat_manager: Union[GroupChatManager, None]):
        """Update the chat manager.

        Args:
            chat_manager (GroupChatManager): the group chat manager
        """
        self._chat_manager = chat_manager

        # Awkward, but due to object cloning, there's no better way to do this
        # Read the GroupChat object from the callback
        self._group_chat = None
        if self._chat_manager is not None:
            for item in self._chat_manager._reply_func_list:
                if isinstance(item["config"], GroupChat):
                    self._group_chat = item["config"]
                    break

    def generate_inner_monologue_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply by running the group chat"""
        if self.chat_manager is None:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        # We want to clear the inner monolgue, keeping only the exteranl chat for context.
        # Reset all the counters and histories, then populate agents with necessary context from the external chat
        self.chat_manager.reset()
        self.update_chat_manager(self.chat_manager)

        external_history = []
        if len(messages) > 1:
            external_history = messages[0 : len(messages) - 1]  # All but the current message

        for agent in self._group_chat.agents:
            agent.reset()
            for message in external_history:
                # Assign each message a name
                attributed_message = message.copy()
                if "name" not in attributed_message:
                    if attributed_message["role"] == "assistant":
                        attributed_message["name"] = self.name
                    else:
                        attributed_message["name"] = sender.name

                self.chat_manager.send(attributed_message, agent, request_reply=False, silent=True)

        try:
            self.initiate_chat(self.chat_manager, message=messages[-1], clear_history=False)
        except:
            traceback.print_exc()

        response_preparer = self.response_preparer
        return True, response_preparer(self, self._group_chat.messages)
