from typing import Dict, List, Protocol


class TransformCondition(Protocol):
    """Defines a contract for transformation condition.

    Classes implementing this protocol should provide a `check_condition` method that takes a list of messages
    and returns a boolean indicating whether to execute the transformation or not.
    This condition is checked whenever a new message is added to the agent associated with the transformation.
    """

    def check_condition(self, messages: List[Dict]) -> bool:
        """Checks whether to apply a transformation or not.

        Args:
            messages: A list of dictionaries representing messages.

        Returns:
            A boolean indicating whether to apply a transformation or not.
        """
        ...


class NewMessageCondition:
    """This condition simply always returns True, which means that the transformation is applied
    whenever a new message is added to the agent.
    """

    def check_condition(self, messages: List[Dict]) -> bool:
        return True
