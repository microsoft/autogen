import _paths
from AppAgents import GreeterAgent
from autogencap.ComponentEnsemble import ComponentEnsemble
from autogencap.DebugLog import Error
from autogencap.proto.CAP_pb2 import Ping


def single_threaded_demo():
    """
    Demonstrates the usage of the CAP platform by registering an actor, connecting to the actor,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform
    ensemble = ComponentEnsemble()
    agent = GreeterAgent(start_thread=False)
    ensemble.register(agent)
    ensemble.connect()
    greeter_link = ensemble.find_by_name("Greeter")
    greeter_link.send_txt_msg("Hello World!")

    no_msg = 0
    while no_msg < 5:
        message = agent.get_message()
        agent.dispatch_message(message)
        if message is None:
            no_msg += 1

    message = agent.get_message()
    agent.dispatch_message(message)

    ensemble.disconnect()


def main():
    single_threaded_demo()


if __name__ == "__main__":
    main()
