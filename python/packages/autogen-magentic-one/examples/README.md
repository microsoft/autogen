# Examples of Magentic-One

**Note**: The examples in this folder are ran at your own risk. They involve agents navigating the web, executing code and browsing local files. Please supervise the execution of the agents to reduce any risks. We also recommend running the examples in a virtual machine or a sandboxed environment.


We include various examples for using Magentic-One and is agents:

- [example.py](example.py): Is [human-in-the-loop] Magentic-One trying to solve a task specified by user input. 



    ```bash

    # Specify logs directory
    python examples/example.py --logs_dir ./my_logs

    # Enable human-in-the-loop mode
    python examples/example.py -logs_dir ./my_logs --hil_mode

    # Save screenshots of browser
    python examples/example.py -logs_dir ./my_logs --save_screenshots
    ```

    Arguments:

    - logs_dir: (Required) Directory for logs, downloads and screenshots of browser (default: current directory)
    - hil_mode: (Optional) Enable human-in-the-loop mode (default: disabled)
    - save_screenshots: (Optional) Save screenshots of browser (default: disabled)


The following examples are for individual agents in Magentic-One:

- [example_coder.py](example_coder.py): Is an example of the Coder + Execution agents in Magentic-One -- without the Magentic-One orchestrator. In a loop, specified by using the RoundRobinOrchestrator, the coder will write code based on user input, executor will run the code and then the user is asked for input again.

- [example_file_surfer.py](example_file_surfer.py): Is an example of the FileSurfer agent individually.  In a loop, specified by using the RoundRobinOrchestrator, the file surfer will respond to user input and then the user is asked for input again.

- [example_userproxy.py](example_userproxy.py): Is an example of the Coder agent in Magentic-One. Compared to [example_coder.py](example_coder.py) this example is just meant to show how to interact with the Coder agent, which serves as a general purpose assistant without tools. In a loop, specified by using the RoundRobinOrchestrator, the coder will respond to user input and then the user is asked for input again.

- [example_websurfer.py](example_websurfer.py): Is an example of the MultimodalWebSurfer agent in Magentic-one -- without the orchestrator. To view the browser the agent uses, pass the argument 'headless = False' to 'actual_surfer.init'. In a loop, specified by using the RoundRobinOrchestrator, the web surfer will perform a single action on the browser in response to user input and then the user is asked for input again.


