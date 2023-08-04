import sys
from typing import Dict, List, Optional, Union
from .agent import Agent
from .responsive_agent import ResponsiveAgent


class GroupChatManager(ResponsiveAgent):
    """(WIP) A chat manager agent that can manage a group chat of multiple agents."""

    agents: List[Agent]
    max_round: int

    def _participant_roles(self):
        return "\n".join([f"{agent.name}: {agent.system_message}" for agent in self.agents])

    def _select_speaker_msg(self):
        return f"""You are in a role play game. The following roles are available:
{self._participant_roles()}. Read the following conversation.
Then select the next role from {self._agent_names} to play. Only return the role."""

    def __init__(
        self,
        max_round: Optional[int] = 10,
        name: Optional[str] = "chat_manager",
        # unlimited consecutive auto reply by default
        max_consecutive_auto_reply: Optional[int] = sys.maxsize,
        human_input_mode: Optional[str] = "NEVER",
        system_message: Optional[str] = "Group chat manager.",
        # seed: Optional[int] = 4,
        **kwargs,
    ):
        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            **kwargs,
        )
        self.register_auto_reply(Agent, self._generate_reply_for_participant)
        self.max_round = max_round
        self._agent_names = []
        self._messages = []
        # self._random = random.Random(seed)

    def _generate_reply_for_participant(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
    ) -> Union[str, Dict, None]:
        self._agent_names = [agent.name for agent in self.agents]
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        for i in range(self.max_round):
            # set the name to speaker's name if the role is not function
            if message["role"] != "function":
                message["name"] = speaker.name
            self._messages.append(message)
            # broadcast the message to all agents except the speaker
            for agent in self.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False)
            if i != self.max_round - 1:
                # speaker selection msg from an agent
                speaker = self._select_speaker(speaker)
                speaker.send(speaker.generate_reply(sender=self), self, request_reply=False)
                message = self.last_message(speaker)
        return True, None

    def _select_speaker(self, last_speaker: Agent):
        """Select the next speaker."""
        self.update_system_message(self._select_speaker_msg())
        final, name = self._generate_oai_reply(self._messages)
        if not final:
            # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
            return self.agents[(self._agent_names.index(last_speaker.name) + 1) % len(self._agent_names)]
        try:
            return self.agent_by_name(name)
        except ValueError:
            return self.agents[(self._agent_names.index(last_speaker.name) + 1) % len(self._agent_names)]

    def agent_by_name(self, name: str) -> Agent:
        """Find the next speaker based on the message."""
        return self.agents[self._agent_names.index(name)]

    def reset(self):
        super().reset()
        self._messages.clear()
