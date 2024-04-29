from typing import Optional

from autogen.agentchat.conversable_agent import ConversableAgent


class SubCriticAgent(ConversableAgent):
    """
    An agent for creating subcriteria from a given list of criteria for evaluating the utility of a given task.
    """

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful assistant to the critic agent. You suggest sub criteria for evaluating different tasks based on the criteria provided by the critic agent (if you feel it is needed).
        They should be distinguishable, quantifiable, and related to the overall theme of the critic's provided criteria.
        You operate by taking in the description of the criteria. You then create a new key called sub criteria where you provide the sub criteria for the given criteria.
        The value of the sub_criteria is a dictionary where the keys are the subcriteria and each value is as follows {"description": sub criteria description , "accepted_values": possible accepted inputs for this key}
        Do this for each criteria provided by the critic (removing the criteria's accepted values). "accepted_values" include the acceptable inputs for each key that are fine-grained and preferably multi-graded levels. "description" includes the criterion description.
        Once you have created the sub criteria for the given criteria, you return the json (make sure to include the contents of the critic's dictionary in the final dictionary as well).
        Make sure to return a valid json and no code"""

    DEFAULT_DESCRIPTION = "An AI agent for creating subcriteria from a given list of criteria."

    def __init__(
        self,
        name="subcritic",
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            description (str): The description of the agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../../conversable_agent#__init__).
        """
        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            **kwargs,
        )
