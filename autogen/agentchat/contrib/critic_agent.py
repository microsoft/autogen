from typing import Callable, Dict, Literal, Optional, Union

from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.runtime_logging import log_new_agent, logging_enabled


class CriticAgent(ConversableAgent):
    """
    An agent for creating list of criteria for evaluating the utility of a given task.
    """

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful assistant. You suggest criteria for evaluating different tasks. They should be distinguishable, quantifiable and not redundant.
    Convert the evaluation criteria into a dictionary where the keys are the criteria and the value of each key is a dictionary as follows {"description": criteria description , "accepted_values": possible accepted inputs for this key}
    Make sure "accepted_values" include the acceptable inputs for each key that are fine-grained and preferably multi-graded levels and "description" includes the criterion description.
    Output just the criteria string you have created, no code.
    """

    DEFAULT_DESCRIPTION = "An AI agent for creating list criteria for evaluating the utility of a given task."

    def __init__(
        self,
        name="critic",
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        **kwargs,
    ):
        """
        Args:
            - name (str): agent name.
            - system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            - description (str): The description of the agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            **kwargs,
        )
