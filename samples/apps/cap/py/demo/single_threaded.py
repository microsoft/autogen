import _paths
from AppAgents import GreeterAgent
from autogencap.DebugLog import Error
from autogencap.proto.CAP_pb2 import Ping
from autogencap.runtime_factory import RuntimeFactory


def single_threaded_demo():
    """
    Demonstrates the usage of the CAP platform by registering an actor, connecting to the actor,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform
    ensemble = RuntimeFactory.get_runtime("ZMQ")
    agent = GreeterAgent(start_thread=False)
    ensemble.register(agent)
    ensemble.connect()
    greeter_link = ensemble.find_by_name("Greeter")
    greeter_link.send_txt_msg("Hello World!")

    no_msg = 0

    # This is where we process the messages in this thread
    # instead of using a separate thread

    # 5 consecutive times with no message received
    # will break the loop
    while no_msg < 5:
        # Get the message for the actor
        message = agent.get_message()
        # Let the actor process the message
        agent.dispatch_message(message)
        # If no message is received, increment the counter otherwise reset it
        no_msg = no_msg + 1 if message is None else 0

    ensemble.disconnect()


def main():
    single_threaded_demo()


if __name__ == "__main__":
    main()
