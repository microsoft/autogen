from typing import Callable, Dict, Literal, Optional, Union

from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.runtime_logging import logging_enabled, log_new_agent


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
        Make sure to return a valid json and not a python dictionary."""

    DEFAULT_DESCRIPTION = "An AI agent for creating subcriteria from a given list of criteria."

    def __init__(
        self,
        name="subcritic",
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        llm_config: Optional[Union[Dict, bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        description: Optional[str] = DEFAULT_DESCRIPTION,
        **kwargs,
    ):
        """
        Args:
            - name (str): agent name.
            - system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            - llm_config (dict or False or None): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
            - max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            - human_input_mode (str): The human input mode for the agent.
                - "ALWAYS": The agent will always require human input.
                - "NEVER": The agent will never require human input.
                - "SOMETIMES": The agent will sometimes require human input.
            - description (str): The description of the agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name=name,
            system_message=system_message,
            human_input_mode="NEVER",
            llm_config=llm_config,
            **kwargs,
        )
