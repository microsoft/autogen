import time
from typing import List

from AppAgents import FidelityAgent, GreeterAgent
from autogencap.DebugLog import Info
from autogencap.LocalActorNetwork import LocalActorNetwork
from autogencap.proto.CAP_pb2 import ActorInfo


def list_agents():
    """
    Demonstrates the usage of the CAP platform by registering an actor, connecting to the actor,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform

    network = LocalActorNetwork()
    # Register an actor
    network.register(GreeterAgent())
    # Register an actor
    network.register(FidelityAgent())
    # Tell actor to connect to other actors
    network.connect()
    # Get a list of actors
    actor_infos: List[ActorInfo] = network.lookup_actor_info(name_regex=".*")
    # Print out all actors found
    Info("list_agents", f"{len(actor_infos)} actors found:")
    for actor_info in actor_infos:
        Info(
            "list_agents",
            f"Name: {actor_info.name}, Namespace: {actor_info.namespace}, Description: {actor_info.description}",
        )
    # Cleanup
    network.disconnect()
