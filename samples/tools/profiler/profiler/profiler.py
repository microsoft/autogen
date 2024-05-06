from dataclasses import dataclass
from typing import Set, List, Optional
import json

from .llm import ChatCompletionService
from .message import Message, OpenAIMessage
from .state import State, StateSpace, DEFAULT_STATE_SPACE


@dataclass
class MessageProfile:

    message: Message
    states: Set[State]  # unorddered collection of states
    cost: Optional[float] = None
    duration: Optional[float] = None

    def __str__(self):
        repr = self.message.source + "\t"
        # repr += f"Cost: {self.cost}\tDuration: {self.duration}\t"
        repr += ", ".join([str(state) for state in self.states])
        content = self.message.content[:40]
        repr += f"\t\t\t{content.encode('unicode_escape').decode()}"
        return repr

    def to_dict(self):
        return {
            "message": self.message.to_dict(),
            "states": [state.to_dict() for state in self.states],
            "cost": self.cost,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data):
        message = Message(**data["message"])
        states = {State(**state) for state in data["states"]}
        cost = data["cost"]
        duration = data["duration"]
        return cls(message=message, states=states, cost=cost, duration=duration)


@dataclass
class ChatProfile:

    message_profiles: List[MessageProfile]  # ordered collection of message profiles

    def __str__(self):
        repr = f"Num messages: {self.num_messages}" + "\n"
        for message_profile in self.message_profiles:
            repr += str(message_profile) + "\n"
        return repr

    def __len__(self):
        return len(self.message_profiles)

    def __iter__(self):
        return iter(self.message_profiles)


class Profiler:

    _STATE_SPACE = DEFAULT_STATE_SPACE

    def __init__(self, state_space: StateSpace = None, llm_service: ChatCompletionService = None):
        """Create a new profiler with a state space and an LLM service.

        Args:
            state_space: The state space to use for profiling messages.
            llm_service: The LLM service to use for profiling messages.

        Raises:
            ValueError: If the state space is not a valid StateSpace instance.
            ValueError: If the LLM service is not a valid ChatCompletionService instance.
        """

        if state_space is not None and not isinstance(state_space, StateSpace):
            raise ValueError("State space is not a valid StateSpace instance.")
        self.state_space = state_space or self._STATE_SPACE

        if not isinstance(llm_service, ChatCompletionService):
            raise ValueError("LLM service is not a valid ChatCompletionService instance.")
        self.llm_service = llm_service

    def profile_message(self, messages: List[Message], idx: int) -> MessageProfile:
        """Profile a message by asking an LLM to select the states that apply to the message.

        Args:
            messages: The list of messages to profile.
            idx: The index of the message to profile.

        Returns:
            The message profile for the message.
        """

        return self._profile_message(messages[idx])

    def _profile_message(self, message: Message) -> MessageProfile:
        """Profile a message by asking an LLM to select the states that apply to the message.

        Args:
            message: The message to profile.

        Returns:
            The message profile for the message.
        """

        def source_or_role_in_tags(state: State) -> bool:
            """Return True if the message source or role is in the state tags."""
            # if state has no tags, the state applies to all roles
            if state.tags is None:
                return True
            return message.source in state.tags or message.role in state.tags

        state_space = self.state_space.filter_states(condition=source_or_role_in_tags)

        state_space_str = ""
        for state in state_space.sorted_states():
            state_space_str += f"{state.name}: {state.description}" + "\n"

        prompt = (
            f"""Which of the following states apply to the message:

List of states:
{state_space_str}

Message
    source: "{message.source}"
    content: "{message.content}"

Only respond with states that apply. States should be return a JSON list in the following format:
Even if only one state applies, it should be returned as a list."""
            + """

{
    "states": [
        {
            "name": ...,
            "description": ...,
        },
        {
            "name": ...,
            "description": ...,
        },
        ...
    ]
}

"""
        )
        response = self.llm_service.create(messages=[OpenAIMessage(role="user", content=prompt)])

        states = json.loads(response.content)["states"]

        extracted_states = []
        for state in states:
            extracted_states.append(State(**state))

        message_profile = MessageProfile(states=extracted_states, message=message)

        return message_profile
