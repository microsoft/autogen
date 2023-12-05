import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple
from autogen import Agent, ConversableAgent, GroupChatManager, GroupChat, OpenAIWrapper


class SocietyOfMindAgent(ConversableAgent):
    """(In preview) A single agent that runs a Group Chat as an inner monologue."""

    def __init__(
        self,
        name: str,
        chat_manager: GroupChatManager,
        response_preparer: Optional[Callable] = lambda messages: messages[-1]["content"].replace("TERMINATE", ""),
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
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

        self.register_reply([Agent, None], SocietyOfMindAgent.generate_group_reply)
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

        # Awkward, but read the GroupChat object from the callback
        self._group_chat = None
        if self._chat_manager is not None:
            for item in self._chat_manager._reply_func_list:
                if isinstance(item["config"], GroupChat):
                    self._group_chat = item["config"]
                    break

    def generate_group_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        if self.chat_manager is None:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        # TODO: Need a cleaner way of doing this to preserve context
        # Reset all the counters and histories, then populate agents with necesssary context from the extennal chat
        self.chat_manager.reset()
        self.update_chat_manager(self.chat_manager)  # Update the group_chat reference

        external_history = []
        if len(messages) > 1:
            external_history = messages[0 : len(messages) - 1]

        for agent in self._group_chat.agents:
            agent.reset()
            # Give each agent external context
            for message in external_history:
                agent.receive(message, self.chat_manager, request_reply=False, silent=True)
        # for message in external_history:
        #    self._group_chat.append(message)

        # Always send to the first agent in the list
        first_agent = self._group_chat.agents[0]
        first_agent.initiate_chat(self.chat_manager, message=messages[-1]["content"], clear_history=False)
        return True, self.response_preparer(self._group_chat.messages)
