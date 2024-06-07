from AppAgents import GreeterAgent
from autogencap.ComponentEnsemble import ComponentEnsemble


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
    greeter_link.send_txt_msg("Hello World!")
    ensemble.disconnect()
