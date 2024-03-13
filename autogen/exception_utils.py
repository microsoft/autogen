from typing import Any


class AgentNameConflict(Exception):
    def __init__(self, msg: str = "Found multiple agents with the same name.", *args: Any, **kwargs: Any):
        super().__init__(msg, *args, **kwargs)


class NoEligibleSpeaker(Exception):
    """Exception raised for early termination of a GroupChat."""

    def __init__(self, message: str = "No eligible speakers."):
        self.message = message
        super().__init__(self.message)


class SenderRequired(Exception):
    """Exception raised when the sender is required but not provided."""

    def __init__(self, message: str = "Sender is required but not provided."):
        self.message = message
        super().__init__(self.message)


class InvalidCarryOverType(Exception):
    """Exception raised when the carryover type is invalid."""

    def __init__(
        self, message: str = "Carryover should be a string or a list of strings. Not adding carryover to the message."
    ):
        self.message = message
        super().__init__(self.message)


class UndefinedNextAgent(Exception):
    """Exception raised when the provided next agents list does not overlap with agents in the group."""

    def __init__(self, message: str = "The provided agents list does not overlap with agents in the group."):
        self.message = message
        super().__init__(self.message)
