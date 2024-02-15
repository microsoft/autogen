class NoEligibleSpeakerException(Exception):
    """Exception raised for early termination of a GroupChat."""

    def __init__(self, message="No eligible speakers."):
        self.message = message
        super().__init__(self.message)


class SenderRequired(Exception):
    """Exception raised when the sender is required but not provided."""

    def __init__(self, message="Sender is required but not provided."):
        self.message = message
        super().__init__(self.message)


class CarryoverType(Exception):
    """Exception raised when the carryover type is invalid."""

    def __init__(
        self, message="Carryover should be a string or a list of strings. Not adding carryover to the message."
    ):
        self.message = message
        super().__init__(self.message)


class UndefinedNextAgent(Exception):
    """Exception raised when the provided next agents list does not overlap with agents in the group."""

    def __init__(self, message="The provided agents list does not overlap with agents in the group"):
        self.message = message
        super().__init__(self.message)
