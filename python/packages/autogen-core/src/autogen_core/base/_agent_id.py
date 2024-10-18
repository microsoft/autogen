from typing_extensions import Self

from ._agent_type import AgentType


class AgentId:
    def __init__(self, type: str | AgentType, key: str) -> None:
        if isinstance(type, AgentType):
            type = type.type

        if type.isidentifier() is False:
            raise ValueError(f"Invalid type: {type}")

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
        items = agent_id.split("/", maxsplit=1)
        if len(items) != 2:
            raise ValueError(f"Invalid agent id: {agent_id}")
        type, key = items[0], items[1]
        return cls(type, key)

    @property
    def type(self) -> str:
        return self._type

    @property
    def key(self) -> str:
        return self._key
