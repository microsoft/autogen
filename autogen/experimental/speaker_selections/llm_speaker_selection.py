import json
import re
from typing import Dict, List

from autogen.experimental.types import SystemMessage

from ..agent import Agent
from ..chat_history import ChatHistoryReadOnly
from ..model_client import ModelClient
from ..speaker_selection import SpeakerSelection


def _mentioned_agents(message_content: str, agents: List[Agent]) -> Dict[str, int]:
    mentions: Dict[str, int] = {}
    for agent in agents:
        # Finds agent mentions, taking word boundaries into account,
        # accommodates escaping underscores and underscores as spaces
        regex = (
            r"(?<=\W)("
            + re.escape(agent.name)
            + r"|"
            + re.escape(agent.name.replace("_", " "))
            + r"|"
            + re.escape(agent.name.replace("_", r"\_"))
            + r")(?=\W)"
        )
        count = len(re.findall(regex, f" {message_content} "))  # Pad the message to help with matching
        if count > 0:
            mentions[agent.name] = count
    return mentions


class LLMSpeakerSelection(SpeakerSelection):
    def __init__(
        self,
        client: ModelClient,
    ) -> None:
        self._model_client = client

    async def _select_text(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Agent:
        select_speaker_message_template = """You are in a role play game. The following roles are available:
                {roles}.
                Read the following conversation.
                Then select the next role from {agent_list} to play. Only return the role."""
        select_speaker_prompt_template = (
            "Read the above conversation. Then select the next role from {agent_list} to play. Only return the role."
        )

        roles = "\n".join([f"{x.name}: {x.description}" for x in agents])
        agent_list = [x.name for x in agents]

        messages = (
            [SystemMessage(select_speaker_message_template.format(roles=roles, agent_list=agent_list))]
            + list(chat_history.messages)
            + [SystemMessage(select_speaker_prompt_template.format(agent_list=agent_list))]
        )
        response = await self._model_client.create(messages, json_output=False)
        assert isinstance(response.content, str)
        mentions = _mentioned_agents(response.content, agents)
        if len(mentions) != 1:
            raise ValueError(f"Expected exactly one agent mention, but got {len(mentions)}")
        agent_name = next(iter(mentions))
        for agent in agents:
            if agent.name == agent_name:
                return agent
        else:
            raise ValueError(f"Agent {agent_name} not found in list of agents")

    async def _select_json(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Agent:
        select_speaker_message_template = """You are in a role play game. The following roles are available:
                {roles}.
                Read the following conversation.
                Then select the next role from {agent_list} to play. Return a JSON object with one property, 'role' set to the role you want to play."""
        select_speaker_prompt_template = "Read the above conversation. Then select the next role from {agent_list} to play. Return a JSON object with one property, 'role' set to the role you want to play."

        roles = "\n".join([f"{x.name}: {x.description}" for x in agents])
        agent_list = [x.name for x in agents]

        messages = (
            [SystemMessage(select_speaker_message_template.format(roles=roles, agent_list=agent_list))]
            + list(chat_history.messages)
            + [SystemMessage(select_speaker_prompt_template.format(agent_list=agent_list))]
        )
        response = await self._model_client.create(messages, json_output=False)
        assert isinstance(response.content, str)
        json_obj = json.loads(response.content)
        if "role" not in json_obj:
            raise ValueError("Expected 'role' property in JSON response")
        agent_name = json_obj["role"]
        for agent in agents:
            if agent.name == agent_name:
                return agent
        else:
            raise ValueError(f"Agent {agent_name} not found in list of agents")

    async def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Agent:
        if self._model_client.capabilities["json_output"]:
            return await self._select_json(agents, chat_history)
        else:
            return await self._select_text(agents, chat_history)
