from typing import Callable, Dict, Literal, Optional, Union

from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.runtime_logging import logging_enabled, log_new_agent


class CriticAgent(ConversableAgent):
    """
    An agent for creating list of criteria for evaluating the utility of a given task.
    """

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful assistant. You suggest criteria for evaluating different tasks. They should be distinguishable, quantifiable and not redundant.
    Convert the evaluation criteria into a dictionary where the keys are the criteria.
    The value of each key is a dictionary as follows {"description": criteria description , "accepted_values": possible accepted inputs for this key}
    Make sure the keys are criteria for assessing the given task.  "accepted_values" include the acceptable inputs for each key that are fine-grained and preferably multi-graded levels. "description" includes the criterion description.
    Return the dictionary."""

    DEFAULT_DESCRIPTION = "An AI agent for creating list criteria for evaluating the utility of a given task."

    def __init__(
        self,
        name="critic",
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
