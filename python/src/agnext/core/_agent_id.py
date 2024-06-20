from typing_extensions import Self


class AgentId:
    def __init__(self, name: str, namespace: str) -> None:
        self._name = name
        self._namespace = namespace

    def __str__(self) -> str:
        return f"{self._namespace}/{self._name}"

    def __hash__(self) -> int:
        return hash((self._namespace, self._name))

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, AgentId):
            return False
        return self._name == value.name and self._namespace == value.namespace

    @classmethod
    def from_str(cls, agent_id: str) -> Self:
        namespace, name = agent_id.split("/")
        return cls(name, namespace)

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def name(self) -> str:
        return self._name
