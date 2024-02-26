# Start Broker & Assistant
# Start UserProxy - Let it run

def remote_ag_demo():
    print("Remote Agent Demo")
    instructions = """
    In this demo, Broker, Assistant, and UserProxy are running in separate processes.
    StandAloneUserProxy.py will initiate a conversation by sending UserProxy a message.
    
    Please do the following:
    1) Start Broker (python demo/StandAloneBroker.py)
    2) Start Assistant (python demo/StandAloneAssistant.py)
    3) Start UserProxy (python demo/StandAloneUserProxy.py)
    """
    input("Press Enter to return to demo menu...")
    pass