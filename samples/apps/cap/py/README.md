# Composable Actor Platform (CAP) for AutoGen

## I just want to run the remote AutoGen agents!
*Python Instructions (Windows, Linux, MacOS):*

pip install autogencap-rajan.jedi

1) AutoGen require OAI_CONFIG_LIST.
   AutoGen python requirements: 3.8 <= python <= 3.11

```

## What is Composable Actor Platform (CAP)?
AutoGen is about Agents and Agent Orchestration.  CAP extends AutoGen to allows Agents to communicate via a message bus.  CAP, therefore, deals with the space between these components.  CAP is a message based, actor platform that allows actors to be composed into arbitrary graphs.

Actors can register themselves with CAP, find other agents, construct arbitrary graphs, send and receive messages independently and many, many, many other things.

```python
# CAP Library
from autogencap.ComponentEnsemble import ComponentEnsemble
from autogencap.Actor import Actor

# A simple Agent
class GreeterAgent(Actor):
    def __init__(self):
        super().__init__(
            agent_name="Greeter",
            description="This is the greeter agent, who knows how to greet people.")

    # Prints out the message it receives
    def on_txt_msg(self, msg):
        print(f"Greeter received: {msg}")
        return True

ensemble = ComponentEnsemble()
# Create an agent
agent = GreeterAgent()
# Register an agent
ensemble.register(agent) # start message processing
# call on_connect() on all Agents
ensemble.connect()
# Get a channel to the agent
greeter_link = ensemble.find_by_name("Greeter")
#Send a message to the agent
greeter_link.send_txt_msg("Hello World!")
# Cleanup
greeter_link.close()
ensemble.disconnect()
```

### Check out other demos in the `py/demo` directory.  We show the following: ###
1) Hello World shown above
2) Many CAP Actors interacting with each other
3) A pair of interacting AutoGen Agents wrapped in CAP Actors
4) CAP wrapped AutoGen Agents in a group chat
5) Two AutoGen Agents running in different processes and communicating through CAP
6) List all registered agents in CAP
7) Run Agent in user supplied message loop
