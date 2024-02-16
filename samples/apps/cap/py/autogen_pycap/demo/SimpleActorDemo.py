import sys
print(sys.path)

import time
from demo.AppAgents import UserInterfaceAgent
from LocalActorNetwork import LocalActorNetwork

def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an agent, connecting to other agents,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform

    network = LocalActorNetwork()
    # Register an agent

    time.sleep(0.01)  # Let the network do things
    network.register(UserInterfaceAgent())
    # Tell agents to connect to other agents

    time.sleep(0.01)  # Let the network do things
    network.connect()
    # Get a channel to the agent

    ui_sender = network.lookup_agent(UserInterfaceAgent.cls_agent_name)
    time.sleep(0.01)  # Let the network do things
    # Send a message to the agent

    ui_sender.send_txt_msg("Hello World!")
    time.sleep(0.01)  # Let the network do things
    # Cleanup

    ui_sender.close()
    network.disconnect()