# Composable Actor Platform (CAP) for AutoGen

## I just want to run the remote AutoGen agents!
*Python Instructions (Windows, Linux, MacOS):*

pip install autogencap

1) AutoGen require OAI_CONFIG_LIST.
   AutoGen python requirements: 3.8 <= python <= 3.11

```

## What is Composable Actor Platform (CAP)?
AutoGen is about Agents and Agent Orchestration.  CAP extends AutoGen to allows Agents to communicate via a message bus.  CAP, therefore, deals with the space between these components.  CAP is a message based, actor platform that allows actors to be composed into arbitrary graphs.

Actors can register themselves with CAP, find other agents, construct arbitrary graphs, send and receive messages independently and many, many, many other things.
```python
    # CAP Platform
    network = LocalActorNetwork()
    # Register an agent
    network.register(GreeterAgent())
    # Tell agents to connect to other agents
    network.connect()
    # Get a channel to the agent
    greeter_link = network.lookup_agent("Greeter")
    # Send a message to the agent
    greeter_link.send_txt_msg("Hello World!")
    # Cleanup
    greeter_link.close()
    network.disconnect()
```
### Check out other demos in the `py/demo` directory.  We show the following: ###
1) Hello World shown above
2) Many CAP Actors interacting with each other
3) A pair of interacting AutoGen Agents wrapped in CAP Actors
4) CAP wrapped AutoGen Agents in a group chat
5) Two AutoGen Agents running in different processes and communicating through CAP
6) List all registered agents in CAP
7) AutoGen integration to list all registered agents
