# Composable Actor Platform (CAP) for AutoGen

## I just want to run the demo!
*Python Instructions (Windows, Linux, MacOS):*

0) cd py
1) pip install -r autogencap/requirements.txt
2) python ./demo/App.py

*Demo Notes:*
1) Options 3, 4, 5 & 6 require OAI_CONFIG_LIST for AutoGen.
   AutoGen python requirements: 3.8 <= python <= 3.11
2) For option 2, type something in and see who receives the message.  Quit to quit.
3) To view any option that displays a chart (such as option 4), you will need to disable Docker code execution. You can do this by setting the environment variable `AUTOGEN_USE_DOCKER` to `False`.

*Demo Reference:*
```
Select the demo app to run:
1. CAP Hello World
2. CAP Complex Agent (e.g. Name or Quit)
3. AutoGen Pair
4. CAP AutoGen Pair
5. AutoGen GroupChat
6. CAP AutoGen GroupChat
Enter your choice (1-6):
```

## What is Composable Actor Platform (CAP)?
AutoGen is about Agents and Agent Orchestration.  CAP for AutoGen deals with the space between these components.  CAP is a message based actor platform that allows actors to be composed into arbitrary graphs.

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

### Coming soon. Stay tuned! ###
1) Two AutoGen Agents running in different processes and communicating through CAP
