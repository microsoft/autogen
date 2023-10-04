from dataclasses import dataclass
import sys
from typing import Dict, List, Optional, Union
from .agent import Agent
from .conversable_agent import ConversableAgent
from .. import oai
import random


@dataclass
class GroupChat:
    """A group chat class that contains a list of agents and the maximum number of rounds."""

    agents: List[ConversableAgent]
    messages: List[Dict]
    max_round: int = 10
    llm_config: Optional[Dict] = None
    admin_name: Optional[str] = None

    @property
    def admin(self):
        """
        if admin_name is None, then return the first agent in the list
        otherwise, return the agent with the name admin_name
        """
        if self.admin_name is None:
            return self.agents[0]
        else:
            return self.agent_by_name(self.admin_name)

    @property
    def agent_names(self) -> List[str]:
        """Return the names of the agents in the group chat."""
        return [agent.name.lower() for agent in self.agents]

    def reset(self):
        """Reset the group chat."""
        self.messages.clear()

    def process_role_play_msgs(self, messages: List[Dict]) -> List[Dict]:
        return [
            {
                "role": "user",
                "content": f"""From {message["name"]}:
{message["content"]}""",
            }
            for message in messages
        ]

    def agent_by_name(self, name: str) -> Agent:
        """Find the next speaker based on the message."""
        return self.agents[self.agent_names.index(name.lower())]

    def next_agent(self, agent: Agent) -> Agent:
        """Return the next agent in the list."""
        return self.agents[(self.agent_names.index(agent.name.lower()) + 1) % len(self.agents)]

    def select_speaker_msgs(self) -> List[Dict]:
        """Return the message for selecting the next speaker."""
        msgs = [
            {
                "role": "system",
                "content": "You are in a role play game. Each conversation must start with 'From {name}:', e.g: From admin: //your message//.",
            }
        ]

        #         # process role information
        #         # each agent introduce the next agent
        #         for i in range(len(self.agents)):
        #             current_agent = self.agents[i]
        #             next_agent = self.next_agent(current_agent)
        #             msgs.append({
        #                 "role": "user",
        #                 "content": f'''From {current_agent.name}:
        # {next_agent.name}, {next_agent.system_message}''',
        #             })

        return msgs

    def select_speaker(self, last_speaker: Agent):
        """Select the next speaker."""
        llm_config = self.llm_config

        # if self.llm_config is None, randomly select
        if llm_config is None:
            # search through its agents and randomly select a llm_config from one of them if it exists
            # shuffle the agents
            llm_configs = [agent.llm_config.copy() for agent in self.agents if isinstance(agent.llm_config, dict)]
            if len(llm_configs) > 0:
                llm_config = random.choice(llm_configs)
            else:
                llm_config = None

        # if llm_config is still None, then return the next agent
        if llm_config is None:
            return self.next_agent(last_speaker)

        
        try:
            system_messages = self.select_speaker_msgs()
            chat_messages = self.process_role_play_msgs(self.messages)
            llm_config["stop"] = [":"]
            msgs = system_messages + chat_messages
            reply = oai.ChatCompletion.create(messages=msgs, **llm_config)
            msg = reply["choices"][0]["message"]["content"]
            name = msg.split(":")[0].split("From ")[1]
            return self.agent_by_name(name)
        except Exception:
            return self.admin

    def _participant_roles(self):
        return "\n".join([f"{agent.name}: {agent.system_message}" for agent in self.agents])


class GroupChatManager(ConversableAgent):
    """(In preview) A chat manager agent that can manage a group chat of multiple agents."""

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
        self.groupchat = groupchat
        self.register_reply(Agent, GroupChatManager.run_chat, config=groupchat, reset_config=GroupChat.reset)
        # self._random = random.Random(seed)

    def _process_received_message(self, message, sender, silent):
        super()._process_received_message(message, sender, silent)
        msg = {
            "content": message,
            "name": sender.name if sender is not None else "Unknown",
        }
        self.groupchat.messages.append(msg)

        # distribute the message to all agents
        msg_with_name = {
            "content": f"""From {msg["name"]}<eof_name>:
{msg["content"]}""",
            "role": "user",
        }
        for agent in self.groupchat.agents:
            if agent != sender:
                self.send(msg_with_name, agent, request_reply=False, silent=True)

    def run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[GroupChat] = None,
    ) -> Union[str, Dict, None]:
        """Run a group chat."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        groupchat = self.groupchat
        for i in range(groupchat.max_round):
            # set the name to speaker's name if the role is not function
            if message["role"] != "function":
                message["name"] = speaker.name
            # self._process_received_message(message, speaker, silent=True)
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # select the next speaker
                speaker = groupchat.select_speaker(speaker)

                # add <eof_name>: as stop sequence if llm_config is not None
                if isinstance(speaker, ConversableAgent) and isinstance(speaker.llm_config, dict):
                    if "stop" in speaker.llm_config:
                        speaker.llm_config["stop"].append("<eof_name>:")
                    else:
                        speaker.llm_config["stop"] = ["<eof_name>:"]
                # let the speaker speak
                reply = speaker.generate_reply(sender=self)
                # restore the stop sequence
                if isinstance(speaker, ConversableAgent) and isinstance(speaker.llm_config, dict):
                    if "stop" in speaker.llm_config:
                        speaker.llm_config["stop"].remove("<eof_name>:")
                
                if reply is None:
                    break
                # if reply is 'From xxx', then set reply to xxx, it's your turn to speak
                if reply.startswith("From ") and reply.split("From ")[1].lower() in groupchat.agent_names:
                    name = reply.split("From ")[1]
                    if name.lower() == speaker.name.lower():
                        agents_except_speaker = [agent for agent in groupchat.agents if agent != speaker]
                        speaker = random.choice(agents_except_speaker)
                    reply = f"{name}, it's your turn to speak."
            except KeyboardInterrupt:
                # let the admin agent speak if interrupted
                if groupchat.admin_name in groupchat.agent_names:
                    # admin agent is one of the participants
                    speaker = groupchat.agent_by_name(groupchat.admin_name)
                    reply = speaker.generate_reply(sender=self)
                else:
                    # admin agent is not found in the participants
                    raise
            if reply is None:
                break
            # The speaker sends the message without requesting a reply
            speaker.send(reply, self, request_reply=False)
            message = self.last_message(speaker)
        return True, None
