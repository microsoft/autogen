from dataclasses import dataclass
import sys
from typing import Dict, List, Optional, Union
from .agent import Agent
from .responsive_agent import ResponsiveAgent


@dataclass
class GroupChat:
    """A group chat class that contains a list of agents and the maximum number of rounds."""

    agents: List[Agent]
    messages: List[Dict]
    max_round: int = 10

    @property
    def agent_names(self) -> List[str]:
        """Return the names of the agents in the group chat."""
        return [agent.name for agent in self.agents]

    def reset(self):
        """Reset the group chat."""
        self.messages.clear()

    def agent_by_name(self, name: str) -> Agent:
        """Find the next speaker based on the message."""
        return self.agents[self.agent_names.index(name)]

    def next_agent(self, agent: Agent) -> Agent:
        """Return the next agent in the list."""
        return self.agents[(self.agent_names.index(agent.name) + 1) % len(self.agents)]

    def select_speaker_msg(self):
        """Return the message for selecting the next speaker."""
        return f"""You are in a role play game. The following roles are available:
{self._participant_roles()}. Read the following conversation.
Then select the next role from {self.agent_names} to play. Only return the role."""

    def select_speaker(self, last_speaker: Agent, selctor: ResponsiveAgent):
        """Select the next speaker."""
        selctor.update_system_message(self.select_speaker_msg())
        final, name = selctor.generate_oai_reply(self.messages)
        if not final:
            # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
            return self.next_agent(last_speaker)
        try:
            return self.agent_by_name(name)
        except ValueError:
            return self.next_agent(last_speaker)

    def _participant_roles(self):
        return "\n".join([f"{agent.name}: {agent.system_message}" for agent in self.agents])


class GroupChatManager(ResponsiveAgent):
    """(WIP) A chat manager agent that can manage a group chat of multiple agents."""

    def __init__(
        self,
        groupchat: GroupChat,
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
            system_message=system_message,
            **kwargs,
        )
        self.register_auto_reply(Agent, GroupChatManager.run_chat, context=groupchat, reset_context=GroupChat.reset)
        # self._random = random.Random(seed)

    def run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        context: Optional[GroupChat] = None,
    ) -> Union[str, Dict, None]:
        """Run a group chat."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        for i in range(context.max_round):
            # set the name to speaker's name if the role is not function
            if message["role"] != "function":
                message["name"] = speaker.name
            context.messages.append(message)
            # broadcast the message to all agents except the speaker
            for agent in context.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False)
            if i != context.max_round - 1:
                # speaker selection msg from an agent
                speaker = context.select_speaker(speaker, self)
                speaker.send(speaker.generate_reply(sender=self), self, request_reply=False)
                message = self.last_message(speaker)
        return True, None
