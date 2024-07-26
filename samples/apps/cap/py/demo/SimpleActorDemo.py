from AppAgents import GreeterAgent
from autogencap.runtime_factory import RuntimeFactory


def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an actor, connecting to the actor,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform
    runtime = RuntimeFactory.get_runtime("ZMQ")
    agent = GreeterAgent()
    runtime.register(agent)
    runtime.connect()
    greeter_link = runtime.find_by_name("Greeter")
    greeter_link.send_txt_msg("Hello World!")
    runtime.disconnect()
