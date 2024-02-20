import time
from AppAgents import UserInterfaceAgent
from autogencap.LocalActorNetwork import LocalActorNetwork


def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an agent, connecting to other agents,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform
    network = LocalActorNetwork()
    # Register an agent
    network.register(UserInterfaceAgent())
    # Tell agents to connect to other agents
    network.connect()
    # Get a channel to the agent
    ui_sender = network.lookup_agent(UserInterfaceAgent.cls_agent_name)
    # Send a message to the agent
    ui_sender.send_txt_msg("Hello World!")
    # Cleanup
    ui_sender.close()
    network.disconnect()
