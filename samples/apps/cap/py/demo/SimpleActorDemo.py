import time
from AppAgents import GreeterAgent
from autogencap.LocalActorNetwork import LocalActorNetwork


def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an actor, connecting to the actor,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform

    network = LocalActorNetwork()
    # Register an actor
    network.register(GreeterAgent())
    # Tell actor to connect to other actors
    network.connect()
    # Get a channel to the actor
    greeter_link = network.lookup_actor("Greeter")
    # Send a message to the actor
    greeter_link.send_txt_msg("Hello World!")
    # Cleanup
    greeter_link.close()
    network.disconnect()
