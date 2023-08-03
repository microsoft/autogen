import sys
from typing import Dict, List, Optional, Tuple, Union
from .agent import Agent
from .responsive_agent import ResponsiveAgent


class GroupChatManager(ResponsiveAgent):
    """(WIP) A chat manager agent that can manage a group chat of multiple agents."""

    agents: List["GroupChatParticipant"]
    max_round: int

    def _participant_roles(self):
        return "\n".join([f"{agent.name}: {agent.system_message}" for agent in self.agents])

    def _select_speaker_msg(self):
        return {
            "role": "system",
            "content": f"""You are in a role play game. The following roles are available:
{self._participant_roles()}. Read the following conversation.
Then select the next role from {self._agent_names} to play. Only return the role.""",
        }

    def __init__(
        self,
        max_round: Optional[int] = 10,
        name: Optional[str] = "chat_manager",
        # unlimited consecutive auto reply by default
        max_consecutive_auto_reply: Optional[int] = sys.maxsize,
        human_input_mode: Optional[str] = "NEVER",
        # seed: Optional[int] = 4,
        **kwargs,
    ):
        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            **kwargs,
        )
        self.register_auto_reply(GroupChatParticipant, self._generate_reply_for_participant)
        self.max_round = max_round
        self._agent_names = []
        self._next_speaker = None
        self._round = 0
        self._messages = []
        # self._random = random.Random(seed)

    def _generate_reply_for_participant(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ) -> Union[str, Dict, None]:
        if messages is None:
            messages = self._oai_messages[sender.name]
        message = messages[-1]
        # set the name to sender's name if the role is not function
        if message["role"] != "function":
            message["name"] = sender.name
        self._messages.append(message)
        self._next_speaker = None
        # broadcast the message to all agents except the sender
        for agent in self.agents:
            if agent != sender:
                self.send(message, agent)
        if self._round == 0:
            self._agent_names = [agent.name for agent in self.agents]
        self._round += 1
        if self._round >= self.max_round:
            return True, None
        # speaker selection msg from an agent
        self._next_speaker = self._select_speaker(sender)
        self._next_speaker.send(self._next_speaker.generate_reply(sender=self), self)
        return True, None

    @property
    def next_speaker(self):
        """Return the next speaker."""
        return self._next_speaker

    def _select_speaker(self, last_speaker: "GroupChatParticipant"):
        """Select the next speaker."""
        final, name = self._generate_oai_reply([self._select_speaker_msg()] + self._messages)
        if not final:
            # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
            name = self._agent_names[(self._agent_names.index(last_speaker.name) + 1) % len(self._agent_names)]
        return self.agent_by_name(name)

    def agent_by_name(self, name: str) -> "GroupChatParticipant":
        """Find the next speaker based on the message."""
        return self.agents[self._agent_names.index(name)]

    def reset(self):
        super().reset()
        self._round = 0
        self._messages.clear()
        self._next_speaker = None


class GroupChatParticipant(ResponsiveAgent):
    """(WIP) A group chat participant agent that can participate in a group chat."""

    group_chat_manager: GroupChatManager

    def __init__(
        self,
        name,
        group_chat_manager=None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            **kwargs,
        )
        self.register_auto_reply(GroupChatManager, self._generate_reply_for_chat_manager)
        self.group_chat_manager = group_chat_manager

    def _generate_reply_for_chat_manager(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate reply for the chat manager."""
        return self.group_chat_manager.next_speaker != self, None


#     def _speaker_selection(self, instruction):
#         """Select the next speaker."""
#         if self.llm_config is False:
#             if self.human_input_mode == "NEVER":
#                 return self.name
#             else:
#                 return self.get_human_input(instruction["content"])
#         sender = self.chat_manager.room
#         roles_msg = {
#             "content": f"""The following roles are available:
# {self._participant_roles()}""",
#             "role": "system",
#         }
#         old_system_msg = self.system_message
#         self.update_system_message(instruction["content"])
#         reply = self._generate_oai_reply([roles_msg] + self.chat_messages[sender.name])
#         self.update_system_message(old_system_msg)
#         return reply
