from dataclasses import dataclass, field


@dataclass(kw_only=True)
class BaseState:
    """Base class for all saveable state"""

    state_type: str = field(default="BaseState")
    version: str = field(default="1.0.0")

    def __post_init__(self) -> None:
        if not self.state_type.isidentifier():
            raise ValueError(
                f"state_type must be a valid identifier: {self.state_type}")
