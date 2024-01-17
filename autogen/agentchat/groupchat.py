import logging
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Tuple


from ..code_utils import content_str
from .agent import Agent
from .conversable_agent import ConversableAgent
from ..graph_utils import check_graph_validity, invert_disallowed_to_allowed, has_self_loops


logger = logging.getLogger(__name__)


class NoEligibleSpeakerException(Exception):
    """Exception raised for early termination of a GroupChat."""

    def __init__(self, message="No eligible speakers."):
        self.message = message
        super().__init__(self.message)


@dataclass
class GroupChat:
    """(In preview) A group chat class that contains the following data fields:
    - agents: a list of participating agents.
    - messages: a list of messages in the group chat.
    - max_round: the maximum number of rounds.
    - admin_name: the name of the admin agent if there is one. Default is "Admin".
        KeyBoardInterrupt will make the admin agent take over.
    - func_call_filter: whether to enforce function call filter. Default is True.
        When set to True and when a message is a function call suggestion,
        the next speaker will be chosen from an agent which contains the corresponding function name
        in its `function_map`.
    - speaker_selection_method: the method for selecting the next speaker. Default is "auto".
        Could be any of the following (case insensitive), will raise ValueError if not recognized:
        - "auto": the next speaker is selected automatically by LLM.
        - "manual": the next speaker is selected manually by user input.
        - "random": the next speaker is selected randomly.
        - "round_robin": the next speaker is selected in a round robin fashion, i.e., iterating in the same order as provided in `agents`.
    - allow_repeat_speaker: whether to allow the same speaker to speak consecutively. Default is True, in which case all speakers are allowed to speak consecutively. If allow_repeat_speaker is a list of Agents, then only those listed agents are allowed to repeat. If set to False, then no speakers are allowed to repeat. allow_repeat_speaker and allowed_or_disallowed_speaker_order are mutually exclusive.
    - allowed_or_disallowed_speaker_order: a dictionary of keys and list as values. The keys are the names of the agents, and the values are the agents that the key agent can transition to. Default is None, in which case a fully connected allowed_speaker_order_dict is assumed. allow_repeat_speaker and allowed_or_disallowed_speaker_order are mutually exclusive.
    - speaker_order_type: whether the speaker_order_type is a dictionary containing lists of allowed agents or disallowed agents. allowed means the allowed_or_disallowed_speaker_order is a dictionary containing lists of allowed agents. If set to disallowed, then the allowed_or_disallowed_speaker_order is a dictionary containing lists of disallowed agents. Must be supplied if allowed_or_disallowed_speaker_order is not None.
    """

    agents: List[Agent]
    messages: List[Dict]
    max_round: Optional[int] = 10
    admin_name: Optional[str] = "Admin"
    func_call_filter: Optional[bool] = True
    speaker_selection_method: Optional[str] = "auto"
    allow_repeat_speaker: Optional[
        Union[bool, List[Agent]]
    ] = None  # It would be set to True if allowed_or_disallowed_speaker_order is None
    allowed_or_disallowed_speaker_order: Optional[Dict] = None
    speaker_order_type: Optional[str] = None

    _VALID_SPEAKER_SELECTION_METHODS = ["auto", "manual", "random", "round_robin"]
    _VALID_SPEAKER_ORDER_TYPE = ["allowed", "disallowed", None]

    allowed_speaker_order_dict: Dict = field(init=False)

    def __post_init__(self):
        # Post init steers clears of the automatically generated __init__ method from dataclass
        # Here, we create allowed_speaker_order_dict from the supplied allowed_or_disallowed_speaker_order and is_allowed_graph, and lastly checks for validity.

        # Check input
        if self.speaker_order_type is not None:
            self.speaker_order_type = self.speaker_order_type.lower()

        assert self.speaker_order_type in self._VALID_SPEAKER_ORDER_TYPE, (
            f"GroupChat speaker_order_type is set to '{self.speaker_order_type}'. "
            f"It should be one of {self._VALID_SPEAKER_ORDER_TYPE} (case insensitive). "
        )

        # If both self.allowed_or_disallowed_speaker_order is None and self.allow_repeat_speaker is None, set allow_repeat_speaker to True to ensure backward compatibility
        # Discussed in https://github.com/microsoft/autogen/pull/857#discussion_r1451541204
        if self.allowed_or_disallowed_speaker_order is None and self.allow_repeat_speaker is None:
            self.allow_repeat_speaker = True

        # self.allowed_or_disallowed_speaker_order and self.allow_repeat_speaker are mutually exclusive parameters.
        # Discussed in https://github.com/microsoft/autogen/pull/857#discussion_r1451266661
        if self.allowed_or_disallowed_speaker_order is not None and self.allow_repeat_speaker is not None:
            raise ValueError(
                "GroupChat allowed_or_disallowed_speaker_order and allow_repeat_speaker cannot both be not None. "
                "Please set one of them to None."
            )

        # Asks the user to specify whether the speaker_order_type is allowed or disallowed if speaker_order_type is supplied
        # Discussed in https://github.com/microsoft/autogen/pull/857#discussion_r1451259524
        if self.allowed_or_disallowed_speaker_order is not None and self.allowed_or_disallowed_speaker_order is None:
            raise ValueError(
                "GroupChat allowed_or_disallowed_speaker_order is not None, but speaker_order_type is None. "
                "Please set speaker_order_type to either 'allowed' or 'disallowed'."
            )

        # Inferring self.allowed_speaker_order_dict
        # Create self.allowed_speaker_order_dict if allowed_or_disallowed_speaker_order is None, using allow_repeat_speaker
        if self.allowed_or_disallowed_speaker_order is None:
            self.allowed_speaker_order_dict = {}

            # Create a fully connected allowed_speaker_order_dict not including self loops
            for agent in self.agents:
                self.allowed_speaker_order_dict[agent.name] = [
                    other_agent for other_agent in self.agents if other_agent != agent
                ]

            # If self.allow_repeat_speaker is True, add self loops to all agents
            if self.allow_repeat_speaker:
                for agent in self.agents:
                    self.allowed_speaker_order_dict[agent.name].append(agent)

            # Else if self.allow_repeat_speaker is a list of Agents, add self loops to the agents in the list
            elif isinstance(self.allow_repeat_speaker, list):
                for agent in self.allow_repeat_speaker:
                    self.allowed_speaker_order_dict[agent.name].append(agent)

        # Create self.allowed_speaker_order_dict if allowed_or_disallowed_speaker_order is not None, using allowed_or_disallowed_speaker_order
        elif self.allowed_or_disallowed_speaker_order is not None:
            # Process based on is_allowed_graph
            if self.speaker_order_type == "allowed":
                self.allowed_speaker_order_dict = self.allowed_or_disallowed_speaker_order
            elif self.speaker_order_type == "disallowed":
                # Logic for processing disallowed allowed_or_disallowed_speaker_order to allowed_speaker_order_dict
                self.allowed_speaker_order_dict = invert_disallowed_to_allowed(
                    self.allowed_or_disallowed_speaker_order, self.agents
                )

        # Inferring self.allow_repeat_speaker from allowed_speaker_order_dict using has_self_loops
        if self.allow_repeat_speaker is None:
            self.allow_repeat_speaker = has_self_loops(self.allowed_speaker_order_dict)

        # Check for validity
        check_graph_validity(
            allowed_speaker_order_dict=self.allowed_speaker_order_dict,
            agents=self.agents,
            allow_repeat_speaker=self.allow_repeat_speaker,
        )

    @property
    def agent_names(self) -> List[str]:
        """Return the names of the agents in the group chat."""
        return [agent.name for agent in self.agents]

    def reset(self):
        """Reset the group chat."""
        self.messages.clear()

    def append(self, message: Dict, speaker: Agent):
        """Append a message to the group chat.
        We cast the content to str here so that it can be managed by text-based
        model.
        """
        # set the name to speaker's name if the role is not function
        # if the role is tool, it is OK to modify the name
        if message["role"] != "function":
            message["name"] = speaker.name
        message["content"] = content_str(message["content"])
        self.messages.append(message)

    def agent_by_name(self, name: str) -> Agent:
        """Returns the agent with a given name."""
        return self.agents[self.agent_names.index(name)]

    def next_agent(self, agent: Agent, agents: Optional[List[Agent]] = None) -> Agent:
        """Return the next agent in the list."""
        if agents is None:
            agents = self.agents

        # What index is the agent? (-1 if not present)
        idx = self.agent_names.index(agent.name) if agent.name in self.agent_names else -1

        # Return the next agent
        if agents == self.agents:
            return agents[(idx + 1) % len(agents)]
        else:
            offset = idx + 1
            for i in range(len(self.agents)):
                if self.agents[(offset + i) % len(self.agents)] in agents:
                    return self.agents[(offset + i) % len(self.agents)]

    def select_speaker_msg(self, agents: Optional[List[Agent]] = None) -> str:
        """Return the system message for selecting the next speaker. This is always the *first* message in the context."""
        if agents is None:
            agents = self.agents
        return f"""You are in a role play game. The following roles are available:
{self._participant_roles(agents)}.

Read the following conversation.
Then select the next role from {[agent.name for agent in agents]} to play. Only return the role."""

    def select_speaker_prompt(self, agents: Optional[List[Agent]] = None) -> str:
        """Return the floating system prompt selecting the next speaker. This is always the *last* message in the context."""
        if agents is None:
            agents = self.agents
        return f"Read the above conversation. Then select the next role from {[agent.name for agent in agents]} to play. Only return the role."

    def manual_select_speaker(self, agents: Optional[List[Agent]] = None) -> Union[Agent, None]:
        """Manually select the next speaker."""
        if agents is None:
            agents = self.agents

        print("Please select the next speaker from the following list:")
        _n_agents = len(agents)
        for i in range(_n_agents):
            print(f"{i+1}: {agents[i].name}")
        try_count = 0
        # Assume the user will enter a valid number within 3 tries, otherwise use auto selection to avoid blocking.
        while try_count <= 3:
            try_count += 1
            if try_count >= 3:
                print(f"You have tried {try_count} times. The next speaker will be selected automatically.")
                break
            try:
                i = input("Enter the number of the next speaker (enter nothing or `q` to use auto selection): ")
                if i == "" or i == "q":
                    break
                i = int(i)
                if i > 0 and i <= _n_agents:
                    return agents[i - 1]
                else:
                    raise ValueError
            except ValueError:
                print(f"Invalid input. Please enter a number between 1 and {_n_agents}.")
        return None

    def _prepare_and_select_agents(
        self, last_speaker: Agent
    ) -> Tuple[Optional[Agent], List[Agent], Optional[List[Dict]], Optional[List[Dict]]]:
        if self.speaker_selection_method.lower() not in self._VALID_SPEAKER_SELECTION_METHODS:
            raise ValueError(
                f"GroupChat speaker_selection_method is set to '{self.speaker_selection_method}'. "
                f"It should be one of {self._VALID_SPEAKER_SELECTION_METHODS} (case insensitive). "
            )

        if not isinstance(self.allow_repeat_speaker, (bool, list)):
            raise ValueError("GroupChat allow_repeat_speaker should be a bool or a list of Agents.")
        # If provided a list, make sure the agent is in the list
        allow_repeat_speaker = (
            self.allow_repeat_speaker
            if isinstance(self.allow_repeat_speaker, bool)
            else last_speaker in self.allow_repeat_speaker
        )

        agents = self.agents
        n_agents = len(agents)
        # Warn if GroupChat is underpopulated
        if n_agents < 2:
            raise ValueError(
                f"GroupChat is underpopulated with {n_agents} agents. "
                "Please add more agents to the GroupChat or use direct communication instead."
            )
        elif n_agents == 2 and self.speaker_selection_method.lower() != "round_robin" and allow_repeat_speaker:
            logger.warning(
                f"GroupChat is underpopulated with {n_agents} agents. "
                "It is recommended to set speaker_selection_method to 'round_robin' or allow_repeat_speaker to False."
                "Or, use direct communication instead."
            )

        if (
            self.func_call_filter
            and self.messages
            and ("function_call" in self.messages[-1] or "tool_calls" in self.messages[-1])
        ):
            funcs = []
            if "function_call" in self.messages[-1]:
                funcs += [self.messages[-1]["function_call"]["name"]]
            if "tool_calls" in self.messages[-1]:
                funcs += [
                    tool["function"]["name"] for tool in self.messages[-1]["tool_calls"] if tool["type"] == "function"
                ]

            # find agents with the right function_map which contains the function name
            agents = [agent for agent in self.agents if agent.can_execute_function(funcs)]
            if len(agents) == 1:
                # only one agent can execute the function
                return agents[0], agents, None
            elif not agents:
                # find all the agents with function_map
                agents = [agent for agent in self.agents if agent.function_map]
                if len(agents) == 1:
                    return agents[0], agents, None
                elif not agents:
                    raise ValueError(
                        f"No agent can execute the function {', '.join(funcs)}. "
                        "Please check the function_map of the agents."
                    )
        # remove the last speaker from the list to avoid selecting the same speaker if allow_repeat_speaker is False
        agents = agents if allow_repeat_speaker else [agent for agent in agents if agent != last_speaker]

        # Filter agents with allowed_speaker_order_dict
        # if last_speaker.name is not a key in allowed_speaker_order_dict, then no agents are eligible
        if last_speaker.name not in self.allowed_speaker_order_dict:
            raise NoEligibleSpeakerException(
                f"Last speaker {last_speaker.name} is not in the allowed_speaker_order_dict."
            )
        else:
            # Extract agent names from the list of agents
            graph_eligible_agents_names = [agent.name for agent in self.allowed_speaker_order_dict[last_speaker.name]]
        # Perform filtering
        graph_eligible_agents = [agent for agent in agents if agent.name in graph_eligible_agents_names]

        # Use the selected speaker selection method
        select_speaker_messages = None
        if self.speaker_selection_method.lower() == "manual":
            selected_agent = self.manual_select_speaker(graph_eligible_agents)
        elif self.speaker_selection_method.lower() == "round_robin":
            selected_agent = self.next_agent(last_speaker, graph_eligible_agents)
        elif self.speaker_selection_method.lower() == "random":
            selected_agent = random.choice(graph_eligible_agents)
        else:
            selected_agent = None
            select_speaker_messages = self.messages.copy()
            # If last message is a tool call or function call, blank the call so the api doesn't throw
            if select_speaker_messages[-1].get("function_call", False):
                select_speaker_messages[-1] = dict(select_speaker_messages[-1], function_call=None)
            if select_speaker_messages[-1].get("tool_calls", False):
                select_speaker_messages[-1] = dict(select_speaker_messages[-1], tool_calls=None)
            select_speaker_messages = select_speaker_messages + [
                {"role": "system", "content": self.select_speaker_prompt(graph_eligible_agents)}
            ]
        return selected_agent, graph_eligible_agents, select_speaker_messages

    def select_speaker(self, last_speaker: Agent, selector: ConversableAgent) -> Agent:
        """Select the next speaker."""
        selected_agent, agents, messages = self._prepare_and_select_agents(last_speaker)
        if selected_agent:
            return selected_agent
        # auto speaker selection
        selector.update_system_message(self.select_speaker_msg(agents))
        final, name = selector.generate_oai_reply(messages)
        return self._finalize_speaker(last_speaker, final, name, agents)

    async def a_select_speaker(self, last_speaker: Agent, selector: ConversableAgent) -> Agent:
        """Select the next speaker."""
        selected_agent, agents, messages = self._prepare_and_select_agents(last_speaker)
        if selected_agent:
            return selected_agent
        # auto speaker selection
        selector.update_system_message(self.select_speaker_msg(agents))
        final, name = await selector.a_generate_oai_reply(messages)
        return self._finalize_speaker(last_speaker, final, name, agents)

    def _finalize_speaker(self, last_speaker: Agent, final: bool, name: str, agents: List[Agent]) -> Agent:
        if not final:
            # the LLM client is None, thus no reply is generated. Use round robin instead.
            return self.next_agent(last_speaker, agents)

        # If exactly one agent is mentioned, use it. Otherwise, leave the OAI response unmodified
        mentions = self._mentioned_agents(name, agents)
        if len(mentions) == 1:
            name = next(iter(mentions))
        else:
            logger.warning(
                f"GroupChat select_speaker failed to resolve the next speaker's name. This is because the speaker selection OAI call returned:\n{name}"
            )

        # Return the result
        try:
            return self.agent_by_name(name)
        except ValueError:
            return self.next_agent(last_speaker, agents)

    def _participant_roles(self, agents: List[Agent] = None) -> str:
        # Default to all agents registered
        if agents is None:
            agents = self.agents

        roles = []
        for agent in agents:
            if agent.description.strip() == "":
                logger.warning(
                    f"The agent '{agent.name}' has an empty description, and may not work well with GroupChat."
                )
            roles.append(f"{agent.name}: {agent.description}".strip())
        return "\n".join(roles)

    def _mentioned_agents(self, message_content: Union[str, List], agents: List[Agent]) -> Dict:
        """Counts the number of times each agent is mentioned in the provided message content.

        Args:
            message_content (Union[str, List]): The content of the message, either as a single string or a list of strings.
            agents (List[Agent]): A list of Agent objects, each having a 'name' attribute to be searched in the message content.

        Returns:
            Dict: a counter for mentioned agents.
        """
        # Cast message content to str
        if isinstance(message_content, dict):
            message_content = message_content["content"]
        message_content = content_str(message_content)

        mentions = dict()
        for agent in agents:
            regex = (
                r"(?<=\W)" + re.escape(agent.name) + r"(?=\W)"
            )  # Finds agent mentions, taking word boundaries into account
            count = len(re.findall(regex, f" {message_content} "))  # Pad the message to help with matching
            if count > 0:
                mentions[agent.name] = count
        return mentions


class GroupChatManager(ConversableAgent):
    """(In preview) A chat manager agent that can manage a group chat of multiple agents."""

    def __init__(
        self,
        groupchat: GroupChat,
        name: Optional[str] = "chat_manager",
        # unlimited consecutive auto reply by default
        max_consecutive_auto_reply: Optional[int] = sys.maxsize,
        human_input_mode: Optional[str] = "NEVER",
        system_message: Optional[Union[str, List]] = "Group chat manager.",
        **kwargs,
    ):
        if kwargs.get("llm_config") and (kwargs["llm_config"].get("functions") or kwargs["llm_config"].get("tools")):
            raise ValueError(
                "GroupChatManager is not allowed to make function/tool calls. Please remove the 'functions' or 'tools' config in 'llm_config' you passed in."
            )

        super().__init__(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            **kwargs,
        )
        # Store groupchat
        self._groupchat = groupchat

        # Order of register_reply is important.
        # Allow sync chat if initiated using initiate_chat
        self.register_reply(Agent, GroupChatManager.run_chat, config=groupchat, reset_config=GroupChat.reset)
        # Allow async chat if initiated using a_initiate_chat
        self.register_reply(
            Agent,
            GroupChatManager.a_run_chat,
            config=groupchat,
            reset_config=GroupChat.reset,
            ignore_async_in_sync_chat=True,
        )

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
            groupchat.append(message, speaker)
            if self._is_termination_msg(message):
                # The conversation is over
                break
            # broadcast the message to all agents except the speaker
            for agent in groupchat.agents:
                if agent != speaker:
                    self.send(message, agent, request_reply=False, silent=True)
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # select the next speaker
                speaker = groupchat.select_speaker(speaker, self)
                # let the speaker speak
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
            except NoEligibleSpeakerException:
                # No eligible speaker, terminate the conversation
                break

            if reply is None:
                break
            # The speaker sends the message without requesting a reply
            speaker.send(reply, self, request_reply=False)
            message = self.last_message(speaker)
            if i == groupchat.max_round - 1:
                groupchat.append(message, speaker)
        return True, None

    async def a_run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[GroupChat] = None,
    ):
        """Run a group chat asynchronously."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        speaker = sender
        groupchat = config
        for i in range(groupchat.max_round):
            groupchat.append(message, speaker)

            if self._is_termination_msg(message):
                # The conversation is over
                break

            # broadcast the message to all agents except the speaker
            for agent in groupchat.agents:
                if agent != speaker:
                    await self.a_send(message, agent, request_reply=False, silent=True)
            if i == groupchat.max_round - 1:
                # the last round
                break
            try:
                # select the next speaker
                speaker = await groupchat.a_select_speaker(speaker, self)
                # let the speaker speak
                reply = await speaker.a_generate_reply(sender=self)
            except KeyboardInterrupt:
                # let the admin agent speak if interrupted
                if groupchat.admin_name in groupchat.agent_names:
                    # admin agent is one of the participants
                    speaker = groupchat.agent_by_name(groupchat.admin_name)
                    reply = await speaker.a_generate_reply(sender=self)
                else:
                    # admin agent is not found in the participants
                    raise
            if reply is None:
                break
            # The speaker sends the message without requesting a reply
            await speaker.a_send(reply, self, request_reply=False)
            message = self.last_message(speaker)
        return True, None

    def _raise_exception_on_async_reply_functions(self) -> None:
        """Raise an exception if any async reply functions are registered.

        Raises:
            RuntimeError: if any async reply functions are registered.
        """
        super()._raise_exception_on_async_reply_functions()

        for agent in self._groupchat.agents:
            agent._raise_exception_on_async_reply_functions()
