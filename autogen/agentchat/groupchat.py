from dataclasses import dataclass
import sys
from typing import Dict, List, Optional, Union

from .. import oai
from .agent import Agent
from .conversable_agent import ConversableAgent
import time

@dataclass
class GroupChat:
    """A group chat class that contains a list of agents and the maximum number of rounds."""

    agents: List[Agent]
    messages: List[Dict]
    max_round: int = 10
    admin_name: str = "Admin"  # the name of the admin agent

    @property
    def agent_names(self) -> List[str]:
        """Return the names of the agents in the group chat."""
        return [agent.name.lower() for agent in self.agents]

    def reset(self):
        """Reset the group chat."""
        self.messages.clear()

    def agent_by_name(self, name: str) -> Agent:
        """Find the next speaker based on the message."""
        return self.agents[self.agent_names.index(name.lower())]

    def next_agent(self, agent: Agent) -> Agent:
        """Return the next agent in the list."""
        return self.agents[(self.agent_names.index(agent.name.lower()) + 1) % len(self.agents)]

    def select_speaker_msgs_original(self) -> List[Dict]:
        """Return the message for selecting the next speaker."""

        return f"""You are in a role play game. The following roles are available:
{self._participant_roles()}.

Read the following conversation.
Then select the next role from {self.agent_names} to play. Only return the role."""
    
    def select_speaker_msgs(self) -> List[Dict]:
        """Return the message for selecting the next speaker."""
        msgs = [
            {
                "role": "system",
                "content": f"You are in a role play game. Each conversation must start with 'From {{name}}:', e.g: From admin: //your message//.",
            }
        ]

        role_msgs = [{
            "role": "user",
            "content": f'''From {self.admin_name}:

            @{agent.name}, {agent.system_message}''',
        } for agent in self.agents]

        # msgs.extend(role_msgs)
        return msgs
    
    def select_speaker_msg_naive(self, chat_history: List[Dict] = None) -> List[Dict]:
        """Return the message for selecting the next speaker."""
        chat_history_prompts = [f"{chat['name']}: {chat['content']}\n" for chat in chat_history]
        msg = f"""###Available speaker###
{self._participant_roles()}.
### End of available speaker ###

### Chat history ###
{''.join(chat_history_prompts)}
### End of chat history ###

Read the chat history above and return the next speaker to carry on the chat history. Only return the speaker name."""
        
        return [{
            "role": "system",
            "content": msg,
        }]

    def process_role_play_msgs(self, messages: List[Dict]) -> List[Dict]:
        return [{
            "role": "user",
            "content": f'''From {message["name"]}:

{message["content"]}''',
        } for message in messages]
    
    def select_speaker(self, last_speaker: Agent, selector: ConversableAgent, mode: Optional[str] = "roleplay"):
        """Select the next speaker."""
        if mode == "next":
            return self.next_agent(last_speaker)
        if mode == "naive":
            final, name = selector.generate_oai_reply(
                self.select_speaker_msg_naive(self.messages)
            )
        elif mode == "roleplay":
            system_messages = self.select_speaker_msgs()
            chat_messages = self.process_role_play_msgs(self.messages)
            old_system_message = selector.system_message
            selector.update_system_message('')
            llm_config = selector.llm_config.copy()
            llm_config["stop"] = [':']
            msgs = system_messages + chat_messages

            reply = oai.ChatCompletion.create(
                messages=msgs, **llm_config
            )
            final = True
            msg = reply['choices'][0]['message']['content']
            selector.update_system_message(old_system_message)
            # msg will be in the form of "From {name}:\n{content}"
            # we need to extract the name using regex
        elif mode == "role_play_original":
            system_messages = self.select_speaker_msgs_original()
            old_system_message = selector.system_message
            selector.update_system_message('')
            final, msg = selector.generate_oai_reply(self.messages + [
                {
                    "role": "system",
                    "content": f"Read the above conversation. Then select the next role from {self.agent_names} to play. Only return the role.",
                }
            ])
            selector.update_system_message(old_system_message)

        if not final:
            # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
            return self.next_agent(last_speaker)
        try:
            if mode == "roleplay":
                name = msg.split(":")[0].split("From ")[1]
            else:
                name = msg
            return self.agent_by_name(name)
        except Exception:
            return self.next_agent(last_speaker)

    def _participant_roles(self) -> str:
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
        mode: Optional[str] = "roleplay", # "roleplay", "naive" or "next"
        **kwargs,
    ):
        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            **kwargs,
        )
        self.mode = mode
        self.register_reply(Agent, GroupChatManager.run_chat, config=groupchat, reset_config=GroupChat.reset)
        # self._random = random.Random(seed)

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
        groupchat = config
        for i in range(groupchat.max_round):
            # set the name to speaker's name if the role is not function
            if message["role"] != "function":
                message["name"] = speaker.name
            groupchat.messages.append(message)
            # broadcast the message to all agents except the speaker
            for agent in groupchat.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False, silent=True)
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # sleep for 10 seconds
                time.sleep(5)
                # select the next speaker
                speaker = groupchat.select_speaker(speaker, self, self.mode)
                if speaker is None:
                    # no speaker is selected
                    reply = None
                    break
                # let the speaker speak
                time.sleep(5)
                reply = speaker.generate_reply(sender=self)
            except KeyboardInterrupt:
                # let the admin agent speak if interrupted
                if groupchat.admin_name in groupchat.agent_names:
                    # admin agent is one of the participants
                    speaker = groupchat.agent_by_name(groupchat.admin_name)
                    reply = speaker.generate_reply(sender=self)
                else:
                    # admin agent is not found in the participants
                    raise
            
            # if reply is None or [TERMINATE] return
            if reply is None or "[TERMINATE]" in reply:
                break
            # The speaker sends the message without requesting a reply
            speaker.send(reply, self, request_reply=False)
            message = self.last_message(speaker)
        return True, None
