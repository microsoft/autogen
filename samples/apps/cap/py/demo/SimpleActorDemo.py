import time
from AppAgents import GreeterAgent
from autogencap.LocalActorNetwork import LocalActorNetwork


def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an agent, connecting to other agents,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform
    network = LocalActorNetwork()
    # Register an agent
    network.register(GreeterAgent())
    # Tell agents to connect to other agents
    network.connect()
    # Get a channel to the agent
    greeter_link = network.lookup_agent("Greeter")
    # Send a message to the agent
    greeter_link.send_txt_msg("Hello World!")
    # Cleanup
    greeter_link.close()
    network.disconnect()
