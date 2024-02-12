"""
This file contains the implementation of various agents used in the application.
Each agent represents a different role and knows how to connect to external systems 
to retrieve information.
"""

from DebugLog import Debug, Info, shorten
from LocalActorNetwork import LocalActorNetwork
from ActorConnector import ActorConnector
from CANActor import CANActor


class FidelityAgent(CANActor):
    """
    This class represents the fidelity agent, who knows how to connect to fidelity to get account,
    portfolio, and order information.

    Args:
        agent_name (str, optional): The name of the agent. Defaults to "Fidelity".
        description (str, optional): A description of the agent. Defaults to "This is the
        fidelity agent who knows how to connect to fidelity to get account, portfolio, and
        order information."
    """

    def __init__(
        self,
        agent_name="Fidelity",
        description="This is the fidelity agent, who knows"
        "how to connect to fidelity to get account, portfolio, and order information.",
    ):
        super().__init__(agent_name, description)


class FinancialPlannerAgent(CANActor):
    """
    This class represents the financial planner agent, who knows how to connect to a financial
    planner and get financial planning information.

    Args:
        agent_name (str, optional): The name of the agent. Defaults to "Financial Planner".
        description (str, optional): A description of the agent. Defaults to "This is the
        financial planner agent, who knows how to connect to a financial planner and get
        financial planning information."
    """

    def __init__(
        self,
        agent_name="Financial Planner",
        description="This is the financial planner"
        " agent, who knows how to connect to a financial planner and get financial"
        " planning information.",
    ):
        super().__init__(agent_name, description)


class QuantAgent(CANActor):
    """
    This class represents the quant agent, who knows how to connect to a quant and get
    quant information.

    Args:
        agent_name (str, optional): The name of the agent. Defaults to "Quant".
        description (str, optional): A description of the agent. Defaults to "This is the
        quant agent, who knows how to connect to a quant and get quant information."
    """

    def __init__(
        self,
        agent_name="Quant",
        description="This is the quant agent, who knows "
        "how to connect to a quant and get quant information.",
    ):
        super().__init__(agent_name, description)


class UserInterfaceAgent(CANActor):
    """
    This class represents the user interface agent, who knows how to connect to a user
    interface and get user interface information.

    Args:
        description (str, optional): A description of the agent. Defaults to "This is the user
        interface agent, who knows how to connect to a user interface and get
        user interface information."
    """

    cls_agent_name = "User interface"

    def __init__(
        self,
        description="This is the user interface agent, who knows how to connect"
        " to a user interface and get user interface information.",
    ):
        super().__init__(UserInterfaceAgent.cls_agent_name, description)


class PersonalAssistant(CANActor):
    """
    This class represents the personal assistant, who knows how to connect to the other agents and
    get information from them.

    Args:
        agent_name (str, optional): The name of the agent. Defaults to "PersonalAssistant".
        description (str, optional): A description of the agent. Defaults to "This is the personal assistant,
        who knows how to connect to the other agents and get information from them."
    """

    cls_agent_name = "PersonalAssistant"

    def __init__(
        self,
        agent_name=cls_agent_name,
        description="This is the personal assistant, who knows how to connect to the other agents and get information from them.",
    ):
        super().__init__(agent_name, description)
        self.fidelity: ActorConnector = None
        self.financial_planner: ActorConnector = None
        self.quant: ActorConnector = None
        self.user_interface: ActorConnector = None

    def connect(self, network: LocalActorNetwork):
        """
        Connects the personal assistant to the specified local actor network.

        Args:
            network (LocalActorNetwork): The local actor network to connect to.
        """
        Debug(self.agent_name, f"is connecting to {network}")
        self.fidelity = network.lookup_agent("Fidelity")
        self.financial_planner = network.lookup_agent("Financial Planner")
        self.quant = network.lookup_agent("Quant")
        self.user_interface = network.lookup_agent("User interface")
        Debug(self.agent_name, "connected")

    def disconnect(self, network: LocalActorNetwork):
        """
        Disconnects the personal assistant from the specified local actor network.

        Args:
            network (LocalActorNetwork): The local actor network to disconnect from.
        """
        super().disconnect(network)
        self.fidelity.close()
        self.financial_planner.close()
        self.quant.close()
        self.user_interface.close()
        Debug(self.agent_name, "disconnected")

    def process_txt_msg(self, msg, msg_type, topic, sender):
        """
        Processes a text message received by the personal assistant.

        Args:
            msg (str): The text message.
            msg_type (str): The type of the message.
            topic (str): The topic of the message.
            sender (str): The sender of the message.

        Returns:
            bool: True if the message was processed successfully, False otherwise.
        """
        Info(self.agent_name, f"Helping user: {shorten(msg)}")
        self.fidelity.send_txt_msg("Help me buy/sell assets for " + msg)
        self.financial_planner.send_txt_msg(
            f"Help me with a financial plan for {msg}'s goals."
        )
        self.quant.send_txt_msg(
            "Help me with some quantitative analysis of the interest rate for " + msg
        )
        self.user_interface.send_txt_msg("Help me talk to " + msg)
        return True
