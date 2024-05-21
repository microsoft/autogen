import time

from AppAgents import GreeterAgent
from autogencap.ComponentEnsemble import ComponentEnsemble
from autogencap.DebugLog import Error
from autogencap.proto.CAP_pb2 import Ping


def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an actor, connecting to the actor,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform
    ensemble = ComponentEnsemble()
    agent = GreeterAgent()
    ensemble.register(agent)
    ensemble.connect()
    greeter_link = ensemble.find_by_name("Greeter")
    ensemble.disconnect()

    ping = Ping()
    # Serialize and send the message
    msg_type_str = Ping.__name__
    msg_bytes = ping.SerializeToString()
    greeter_link.send_txt_msg("Hello World!")
    greeter_link.send_bin_msg(msg_type_str, msg_bytes)
    _, resp_type, resp_msg_bytes = greeter_link.send_recv_msg(msg_type_str, msg_bytes)
