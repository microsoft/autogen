from dataclasses import dataclass
from typing import List, Set, Callable, Optional


@dataclass
class State:
    """A state is a representation of a particular states."""

    name: str
    description: str
    tags: Optional[List[str]] = None

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
    """A state space is a collection of states that represent the possible states."""

    states: Set[State]

    def __str__(self):
        return ", ".join([str(state) for state in self.states])

    def __iter__(self):
        return iter(self.states)

    def filter_states(self, condition: Callable[[State], bool]) -> "StateSpace":
        filtered_states = {state for state in self.states if condition(state)}
        return StateSpace(filtered_states)


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
        State(name="TERMINATE", description="The agent's message contains the word 'TERMINATE'", tags=["assistant"]),
        State(name="EMPTY", description="The message is empty", tags=["user"]),
        State(
            name="UNDEFINED",
            description="Use this code when the message does not fit any of the other codes",
            tags=["user", "assistant"],
        ),
    }
)
