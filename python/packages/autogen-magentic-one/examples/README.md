# Examples of Magentic-One

**Note**: The examples in this folder are ran at your own risk. They involve agents navigating the web, executing code and browsing local files. Please supervise the execution of the agents to reduce any risks. We also recommend running the examples in a docker environment.


We include various examples for using Magentic-One and is agents:

- [example.py](example.py): Is a human-in-the-loop of Magentic-One trying to solve a task specified by user input. If you wish for the team to execute the task without involving the user, remove user_proxy from the Orchestrator agents list.

- [example_coder.py](example_coder.py): Is an example of the Coder + Execution agents in Magentic-One -- without the Magentic-One orchestrator. In a loop, specified by using the RoundRobinOrchestrator, the coder will write code based on user input, executor will run the code and then the user is asked for input again.

- [example_file_surfer.py](example_file_surfer.py): Is an example of the FileSurfer agent individually.  In a loop, specified by using the RoundRobinOrchestrator, the file surfer will respond to user input and then the user is asked for input again.

- [example_userproxy.py](example_userproxy.py): Is an example of the Coder agent in Magentic-One. Compared to [example_coder.py](example_coder.py) this example is just meant to show how to interact with the Coder agent, which serves as a general purpose assistant without tools. In a loop, specified by using the RoundRobinOrchestrator, the coder will respond to user input and then the user is asked for input again.

- [example_websurfer.py](example_websurfer.py): Is an example of the MultimodalWebSurfer agent in Magentic-one -- without the orchestrator. To view the browser the agent uses, pass the argument 'headless = False' to 'actual_surfer.init'. In a loop, specified by using the RoundRobinOrchestrator, the web surfer will perform a single action on the browser in response to user input and then the user is asked for input again.


Running these examples is simple. First make sure you have installed 'autogen-magentic-one' either from source or from pip, then run 'python example.py'
