from dataclasses import dataclass
from typing import List, Set, Callable

from ..database.database import ChatMessage
from ..llm import OpenAIMessage, ChatCompletionService


@dataclass
class State:

    name: str
    description: str
    tags: List[str]

    def __str__(self):
        return f"{self.name}"

    def __eq__(self, other):
        if isinstance(other, State):
            return self.name == other.name and self.description == other.description and self.tags == other.tags
        return False

    def __hash__(self):
        return hash((self.name, self.description, tuple(self.tags)))


@dataclass
class StateSpace:

    states: Set[State]

    def __str__(self):
        return " ".join([str(state) for state in self.states])

    def filter_states(self, condition: Callable[[State], bool]) -> "StateSpace":
        filtered_states = {state for state in self.states if condition(state)}
        return StateSpace(filtered_states)


@dataclass
class MessageProfile:

    message: ChatMessage
    cost: float
    duration: float
    states: Set[State]  # unorddered collection of states

    def __str__(self):
        repr = f"Cost: {self.cost}\tDuration: {self.duration}\t"
        for state in self.states:
            repr += str(state) + " "
        return repr


@dataclass
class ChatProfile:

    num_messages: int
    message_profiles: List[MessageProfile]  # ordered collection of message profiles

    def __str__(self):
        repr = f"Num messages: {self.num_messages}" + "\n"
        for message_profile in self.message_profiles:
            repr += str(message_profile) + "\n"
        return repr


class Profiler:

    DEFAULT_STATE_SPACE = StateSpace(
        states={
            State(
                name="USER-REQUEST",
                description="The message shows the *user* requesting a task that needs to be completed",
                tags=["user"],
            ),
            State(
                name="CODING",
                description="The message shows the assistant writing python or shell code to solve a problem. IE the message contains code blocks. This code does not apply to markdown code blocks",
                tags=["assistant"],
            ),
            State(
                name="PLANNING",
                description="The message shows that the agent is create a step by step plan to accomplish some task.",
                tags=["assistant"],
            ),
            State(
                name="ANALYSING-RESULTS",
                description="The assistant's message is reflecting on results obtained so far",
                tags=["assistant"],
            ),
            State(
                name="CODE-EXECUTION",
                description="The user shared results of code execution, e.g., results, logs, error trace",
                tags=["user"],
            ),
            State(
                name="CODE-EXECUTION-ERROR",
                description="The user shared results of code execution and they show an error in execution",
                tags=["user"],
            ),
            State(
                name="CODE-EXECUTION-SUCCESS",
                description="The user shared results of code execution and they show a successful execution",
                tags=["user"],
            ),
            State(
                name="CODING-TOOL-USE",
                description="The message contains a code block and the code uses method from the `functions` module eg indicated by presence of `from functions import....`",
                tags=["assistant"],
            ),
            State(
                name="ASKING-FOR-INFO",
                description="The assistant is asking a question",
                tags=["assistant"],
            ),
            State(
                name="SUMMARIZING",
                description="The assistant is synthesizing/summarizing information gathered so far",
                tags=["assistant"],
            ),
            State(
                name="TERMINATE", description="The agent's message contains the word 'TERMINATE'", tags=["assistant"]
            ),
            State(name="EMPTY", description="The message is empty", tags=["user"]),
            State(
                name="UNDEFINED",
                description="Use this code when the message does not fit any of the other codes",
                tags=["user", "assistant"],
            ),
        }
    )

    def __init__(self, state_space: StateSpace = None, llm_service: ChatCompletionService = None):

        if state_space is not None and not isinstance(state_space, StateSpace):
            raise ValueError("State space is not a valid StateSpace instance.")
        self.state_space = state_space or self.DEFAULT_STATE_SPACE

        if not isinstance(llm_service, ChatCompletionService):
            raise ValueError("LLM service is not a valid ChatCompletionService instance.")
        self.llm_service = llm_service

    def profile_message(self, message: ChatMessage) -> MessageProfile:

        def role_in_tags(state: State) -> bool:
            # if state has no tags, the state applies to all roles
            if state.tags is None:
                return True
            return message.role in state.tags

        state_space = self.state_space.filter_states(condition=role_in_tags)
        state_space_str = ""

        for state in state_space.states:
            state_space_str += f"{state.name}: {state.description}" + "\n"

        prompt = f"""Which of the following codes apply to the message:
List of codes:
{state_space_str}

Message
    role: "{message.role}"
    content: "{message.content}"

Only respond with codes that apply. Codes should be separated by commas.
    """
        response_msg = self.llm_service.create(messages=[OpenAIMessage(role="user", content=prompt)])

        extracted_states_names = response_msg.content.split(",")
        extracted_states = []
        for state_name in extracted_states_names:
            extracted_states.append(State(name=state_name, description="", tags=[]))

        message_profile = MessageProfile(cost=0, duration=0, states=extracted_states, message=message)

        return message_profile
