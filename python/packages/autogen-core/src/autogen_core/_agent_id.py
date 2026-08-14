import re

from typing_extensions import Self

from ._agent_type import AgentType


def is_valid_agent_type(value: str) -> bool:
    return bool(re.match(r"^[\w\-\.]+\Z", value))


class AgentId:
    """
    Agent ID uniquely identifies an agent instance within an agent runtime - including distributed runtime. It is the 'address' of the agent instance for receiving messages.

    See here for more information: :ref:`agentid_and_lifecycle`
    """

    def __init__(self, type: str | AgentType, key: str) -> None:
        if isinstance(type, AgentType):
            type = type.type

        if not is_valid_agent_type(type):
            raise ValueError(rf"Invalid agent type: {type}. Allowed values MUST match the regex: `^[\w\-\.]+\Z`")

        self._type = type
        self._key = key

    def __hash__(self) -> int:
        return hash((self._type, self._key))

    def __str__(self) -> str:
        return f"{self._type}/{self._key}"

    def __repr__(self) -> str:
        return f'AgentId(type="{self._type}", key="{self._key}")'

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, AgentId):
            return False
        return self._type == value.type and self._key == value.key

    @classmethod
    def from_str(cls, agent_id: str) -> Self:
        """Convert a string of the format ``type/key`` into an AgentId"""
        items = agent_id.split("/", maxsplit=1)
        if len(items) != 2:
            raise ValueError(f"Invalid agent id: {agent_id}")
        type, key = items[0], items[1]
        return cls(type, key)

    @property
    def type(self) -> str:
        """
        An identifier that associates an agent with a specific factory function.

        Strings may only be composed of alphanumeric letters (a-z) and (0-9), or underscores (_).
        """
        return self._type

    @property
    def key(self) -> str:
        """
        Agent instance identifier.

        Strings may only be composed of alphanumeric letters (a-z) and (0-9), or underscores (_).
        """
        return self._key
