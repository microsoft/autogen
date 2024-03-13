# Start Broker & Assistant
# Start UserProxy - Let it run


def remote_ag_demo():
    print("Remote Agent Demo")
    instructions = """
    In this demo, Broker, Assistant, and UserProxy are running in separate processes.
    demo/standalone/UserProxy.py will initiate a conversation by sending UserProxy a message.

    Please do the following:
    1) Start Broker (python demo/standalone/Broker.py)
    2) Start Assistant (python demo/standalone/Assistant.py)
    3) Start UserProxy (python demo/standalone/UserProxy.py)
    """
    print(instructions)
    input("Press Enter to return to demo menu...")
    pass
