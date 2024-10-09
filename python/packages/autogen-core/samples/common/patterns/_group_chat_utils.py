"""Credit to the original authors: https://github.com/microsoft/autogen/blob/main/autogen/agentchat/groupchat.py"""

import re
from typing import Dict, List

from autogen_core.base import AgentProxy
from autogen_core.components.model_context import ChatCompletionContext
from autogen_core.components.models import ChatCompletionClient, SystemMessage, UserMessage


async def select_speaker(context: ChatCompletionContext, client: ChatCompletionClient, agents: List[AgentProxy]) -> int:
    """Selects the next speaker in a group chat using a ChatCompletion client."""
    # TODO: Handle multi-modal messages.

    # Construct formated current message history.
    history_messages: List[str] = []
    for msg in await context.get_messages():
        assert isinstance(msg, UserMessage) and isinstance(msg.content, str)
        history_messages.append(f"{msg.source}: {msg.content}")
    history = "\n".join(history_messages)

    # Construct agent roles.
    roles = "\n".join(
        [f"{(await agent.metadata)['type']}: {(await agent.metadata)['description']}".strip() for agent in agents]
    )

    # Construct agent list.
    participants = str([(await agent.metadata)["type"] for agent in agents])

    # Select the next speaker.
    select_speaker_prompt = f"""You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
"""
    select_speaker_messages = [SystemMessage(select_speaker_prompt)]
    response = await client.create(messages=select_speaker_messages)
    assert isinstance(response.content, str)
    mentions = await mentioned_agents(response.content, agents)
    if len(mentions) != 1:
        raise ValueError(f"Expected exactly one agent to be mentioned, but got {mentions}")
    agent_name = list(mentions.keys())[0]
    # Get the index of the selected agent by name
    agent_index = 0
    for i, agent in enumerate(agents):
        if (await agent.metadata)["type"] == agent_name:
            agent_index = i
            break

    assert agent_index is not None
    return agent_index


async def mentioned_agents(message_content: str, agents: List[AgentProxy]) -> Dict[str, int]:
    """Counts the number of times each agent is mentioned in the provided message content.
    Agent names will match under any of the following conditions (all case-sensitive):
    - Exact name match
    - If the agent name has underscores it will match with spaces instead (e.g. 'Story_writer' == 'Story writer')
    - If the agent name has underscores it will match with '\\_' instead of '_' (e.g. 'Story_writer' == 'Story\\_writer')

    Args:
        message_content (Union[str, List]): The content of the message, either as a single string or a list of strings.
        agents (List[Agent]): A list of Agent objects, each having a 'name' attribute to be searched in the message content.

    Returns:
        Dict: a counter for mentioned agents.
    """
    mentions: Dict[str, int] = dict()
    for agent in agents:
        # Finds agent mentions, taking word boundaries into account,
        # accommodates escaping underscores and underscores as spaces
        name = (await agent.metadata)["type"]
        regex = (
            r"(?<=\W)("
            + re.escape(name)
            + r"|"
            + re.escape(name.replace("_", " "))
            + r"|"
            + re.escape(name.replace("_", r"\_"))
            + r")(?=\W)"
        )
        count = len(re.findall(regex, f" {message_content} "))  # Pad the message to help with matching
        if count > 0:
            mentions[name] = count
    return mentions
