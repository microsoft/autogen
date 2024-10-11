"""
This file contains the implementation of various agents used in the application.
Each agent represents a different role and knows how to connect to external systems
to retrieve information.
"""

from autogencap.Actor import Actor
from autogencap.actor_runtime import IRuntime
from autogencap.ActorConnector import ActorConnector
from autogencap.DebugLog import Debug, Info, shorten
from autogencap.runtime_factory import RuntimeFactory


class GreeterAgent(Actor):
    """
    Prints message to screen
    """

    def __init__(
        self,
        start_thread=True,
        agent_name="Greeter",
        description="This is the greeter agent, who knows how to greet people.",
    ):
        super().__init__(agent_name, description, start_thread=start_thread)


class FidelityAgent(Actor):
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
        description=(
            "This is the fidelity agent, who knows"
            "how to connect to fidelity to get account, portfolio, and order information."
        ),
    ):
        super().__init__(agent_name, description)


class FinancialPlannerAgent(Actor):
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
        description=(
            "This is the financial planner"
            " agent, who knows how to connect to a financial planner and get financial"
            " planning information."
        ),
    ):
        super().__init__(agent_name, description)


class QuantAgent(Actor):
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
        description="This is the quant agent, who knows " "how to connect to a quant and get quant information.",
    ):
        super().__init__(agent_name, description)


class RiskManager(Actor):
    """
    This class represents a risk manager, who will analyze portfolio risk.

    Args:
        description (str, optional): A description of the agent. Defaults to "This is the user
        interface agent, who knows how to connect to a user interface and get
        user interface information."
    """

    cls_agent_name = "Risk Manager"

    def __init__(
        self,
        description=(
            "This is the user interface agent, who knows how to connect"
            " to a user interface and get user interface information."
        ),
    ):
        super().__init__(RiskManager.cls_agent_name, description)


class PersonalAssistant(Actor):
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
        self.risk_manager: ActorConnector = None

    def on_connect(self, network: IRuntime):
        """
        Connects the personal assistant to the specified local actor network.

        Args:
            network (LocalActorNetwork): The local actor network to connect to.
        """
        Debug(self.actor_name, f"is connecting to {network}")
        self.fidelity = network.find_by_name("Fidelity")
        self.financial_planner = network.find_by_name("Financial Planner")
        self.quant = network.find_by_name("Quant")
        self.risk_manager = network.find_by_name("Risk Manager")
        Debug(self.actor_name, "connected")

    def disconnect_network(self, network: IRuntime):
        """
        Disconnects the personal assistant from the specified local actor network.

        Args:
            network (LocalActorNetwork): The local actor network to disconnect from.
        """
        super().disconnect_network(network)
        self.fidelity.close()
        self.financial_planner.close()
        self.quant.close()
        self.risk_manager.close()
        Debug(self.actor_name, "disconnected")

    def on_txt_msg(self, msg, msg_type, topic, sender):
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
        if msg.strip().lower() != "quit" and msg.strip().lower() != "":
            Info(self.actor_name, f"Helping user: {shorten(msg)}")
            self.fidelity.send_txt_msg(f"I, {self.actor_name}, need your help to buy/sell assets for " + msg)
            self.financial_planner.send_txt_msg(
                f"I, {self.actor_name}, need your help in creating a financial plan for {msg}'s goals."
            )
            self.quant.send_txt_msg(
                f"I, {self.actor_name}, need your help with quantitative analysis of the interest rate for " + msg
            )
            self.risk_manager.send_txt_msg(f"I, {self.actor_name}, need your help in analyzing {msg}'s portfolio risk")
        return True
