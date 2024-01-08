import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple
from autogen import Agent, ConversableAgent, GroupChatManager, GroupChat, OpenAIWrapper


class SocietyOfMindAgent(ConversableAgent):
    """(In preview) A single agent that runs a Group Chat as an inner monologue.
    At the end of the conversation (termination for any reason), the SocietyOfMindAgent
    applies the response_preparer method on the entire inner monologue message history to
    extract a final answer for the reply.

    Most arguments are inherited from ConversableAgent. New arguments are:
        chat_manager (GroupChatManager): the group chat manager that will be running the inner monologue
        response_preparer (Optional, Callable): A function reference of the form:
                    f( self: SocietyOfMindAgent, messages: List[Dict])
                Where self is this SocietyOfMindAgent, and messages is a list of inner-monologue messages. The
                function should return a string representing the final response (extracted or prepared) from
                that history. The default response_preparer deterministically returns the last message in the
                inner-monolgue, but strips out any termination signals.
    """

    def __init__(
        self,
        name: str,
        chat_manager: GroupChatManager,
        response_preparer: Optional[Union[str, Callable]] = lambda self, messages: messages[-1]["content"]
        .replace("TERMINATE", "")
        .strip(),
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
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
        )

        self.update_chat_manager(chat_manager)
        self.response_preparer = response_preparer

        self._reply_func_list = []
        self.register_reply([Agent, None], SocietyOfMindAgent.generate_inner_monologue_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

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
        # Reset all the counters and histories, then populate agents with necesssary context from the extennal chat
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

        self.initiate_chat(self.chat_manager, message=messages[-1], clear_history=False)
        return True, self.response_preparer(self, self._group_chat.messages)
