# Magentic-One

> [!CAUTION]
> Using Magentic-One involves interacting with a digital world designed for humans, which carries inherent risks. To minimize these risks, consider the following precautions:
>
> 1. **Use Containers**: Run all tasks in docker containers to isolate the agents and prevent direct system attacks.
> 2. **Virtual Environment**: Use a virtual environment to run the agents and prevent them from accessing sensitive data.
> 3. **Monitor Logs**: Closely monitor logs during and after execution to detect and mitigate risky behavior.
> 4. **Human Oversight**: Run the examples with a human in the loop to supervise the agents and prevent unintended consequences.
> 5. **Limit Access**: Restrict the agents' access to the internet and other resources to prevent unauthorized actions.
> 6. **Safeguard Data**: Ensure that the agents do not have access to sensitive data or resources that could be compromised. Do not share sensitive information with the agents.
> Be aware that agents may occasionally attempt risky actions, such as recruiting humans for help or accepting cookie agreements without human involvement. Always ensure agents are monitored and operate within a controlled environment to prevent unintended consequences. Moreover, be cautious that Magentic-One may be susceptible to prompt injection attacks from webpages.

> [!NOTE]
> This code is currently being ported to AutoGen AgentChat. If you want to build on top of Magentic-One, we recommend waiting for the port to be completed. In the meantime, you can use this codebase to experiment with Magentic-One.


We are introducing Magentic-One, our new generalist multi-agent system for solving open-ended web and file-based tasks across a variety of domains. Magentic-One represents a significant step towards developing agents that can complete tasks that people encounter in their work and personal lives.

![](./imgs/autogen-magentic-one-example.png)

> _Example_: Suppose a user requests the following: _Can you rewrite the readme of the autogen GitHub repository to be more clear_. Magentic-One will use the following process to handle this task. The Orchestrator agent will break down the task into subtasks and assign them to the appropriate agents. In this case, the WebSurfer will navigate to GiHub, search for the autogen repository, and extract the readme file. Next the Coder agent will rewrite the readme file for clarity and return the updated content to the Orchestrator. At each point, the Orchestrator will monitor progress via a ledger, and terminate when the task is completed successfully.

## Architecture

<!-- <center>
<img src="./imgs/autgen" alt="drawing" style="width:350px;"/>
</center> -->

![](./imgs/autogen-magentic-one-agents.png)

Magentic-One uses agents with the following personas and capabilities:

- Orchestrator: The orchestrator agent is responsible for planning, managing subgoals, and coordinating the other agents. It can break down complex tasks into smaller subtasks and assign them to the appropriate agents. It also keeps track of the overall progress and takes corrective actions if needed (such as reassigning tasks or replanning when stuck).

- Coder: The coder agent is skilled in programming languages and is responsible for writing code.

- Computer Terminal: The computer terminal agent acts as the interface that can execute code written by the coder agent.

- Web Surfer: The web surfer agent is proficient is responsible for web-related tasks. It can browse the internet, retrieve information from websites, and interact with web-based applications. It can handle interactive web pages, forms, and other web elements.

- File Surfer: The file surfer agent specializes in navigating files such as pdfs, powerpoints, WAV files, and other file types. It can search, read, and extract information from files.

We created Magentic-One with one agent of each type because their combined abilities help tackle tough benchmarks. By splitting tasks among different agents, we keep the code simple and modular, like in object-oriented programming. This also makes each agent's job easier since they only need to focus on specific tasks. For example, the websurfer agent only needs to navigate webpages and doesn't worry about writing code, making the team more efficient and effective.

### Planning and Tracking Task Progress

<center>
<img src="./imgs/autogen-magentic-one-arch.png" alt="drawing" style=""/>
</center>

The figure illustrates the workflow of an orchestrator managing a multi-agent setup, starting with an initial prompt or task. The orchestrator creates or updates a ledger with gathered information, including verified facts, facts to look up, derived facts, and educated guesses. Using this ledger, a plan is derived, which consists of a sequence of steps and task assignments for the agents. Before execution, the orchestrator clears the agents' contexts to ensure they start fresh. The orchestrator then evaluates if the request is fully satisfied. If so, it reports the final answer or an educated guess.

If the request is not fully satisfied, the orchestrator assesses whether the work is progressing or if there are significant barriers. If progress is being made, the orchestrator orchestrates the next step by selecting an agent and providing instructions. If the process stalls for more than two iterations, the ledger is updated with new information, and the plan is adjusted. This cycle continues, iterating through steps and evaluations, until the task is completed. The orchestrator ensures organized, effective tracking and iterative problem-solving to achieve the prompt's goal.

Note that many parameters such as terminal logic and maximum number of stalled iterations are configurable. Also note that the orchestrator cannot instantiate new agents. This is possible but not implemented in Magentic-One.
  |

### Logging in Team One Agents

Team One agents can emit several log events that can be consumed by a log handler (see the example log handler in [utils.py](src/autogen_magentic_one/utils.py)). A list of currently emitted events are:

- OrchestrationEvent : emitted by a an [Orchestrator](src/autogen_magentic_one/agents/base_orchestrator.py) agent.
- WebSurferEvent : emitted by a [WebSurfer](src/autogen_magentic_one/agents/multimodal_web_surfer/multimodal_web_surfer.py) agent.

In addition, developers can also handle and process logs generated from the AutoGen core library (e.g., LLMCallEvent etc). See the example log handler in [utils.py](src/autogen_magentic_one/utils.py) on how this can be implemented. By default, the logs are written to a file named `log.jsonl` which can be configured as a parameter to the defined log handler. These logs can be parsed to retrieved data agent actions.

# Setup and Usage

You can install the Magentic-One package and then run the example code to see how the agents work together to accomplish a task.

1. Clone the code and install the package:

```bash
git clone -b staging https://github.com/microsoft/autogen.git
cd autogen/python/packages/autogen-magentic-one
pip install -e .
```

The following instructions are for running the example code:

2. Configure the environment variables for the chat completion client. See instructions below [Environment Configuration for Chat Completion Client](#environment-configuration-for-chat-completion-client).
3. Magentic-One code uses code execution, you need to have [Docker installed](https://docs.docker.com/engine/install/) to run any examples.
4. Magentic-One uses playwright to interact with web pages. You need to install the playwright dependencies. Run the following command to install the playwright dependencies:

```bash
playwright install-deps
```
5. Now you can run the example code to see how the agents work together to accomplish a task.

> [!CAUTION]  
> The example code may download files from the internet, execute code, and interact with web pages. Ensure you are in a safe environment before running the example code. 

> [!NOTE]
> You will need to ensure Docker is running prior to running the example. 

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

6. [Preview] We have a preview API for Magentic-One. 
 You can use the `MagenticOneHelper` class to interact with the system. See the [interface README](interface/README.md) for more details.


## Environment Configuration for Chat Completion Client

This guide outlines how to configure your environment to use the `create_completion_client_from_env` function, which reads environment variables to return an appropriate `ChatCompletionClient`.

Currently, Magentic-One only supports OpenAI's GPT-4o as the underlying LLM.

### Azure with Active Directory

To configure for Azure with Active Directory, set the following environment variables:

- `CHAT_COMPLETION_PROVIDER='azure'`
- `CHAT_COMPLETION_KWARGS_JSON` with the following JSON structure:

```json
{
  "api_version": "2024-02-15-preview",
  "azure_endpoint": "REPLACE_WITH_YOUR_ENDPOINT",
  "model_capabilities": {
    "function_calling": true,
    "json_output": true,
    "vision": true
  },
  "azure_ad_token_provider": "DEFAULT",
  "model": "gpt-4o-2024-05-13"
}
```

### With OpenAI

To configure for OpenAI, set the following environment variables:

- `CHAT_COMPLETION_PROVIDER='openai'`
- `CHAT_COMPLETION_KWARGS_JSON` with the following JSON structure:

```json
{
  "api_key": "REPLACE_WITH_YOUR_API",
  "model": "gpt-4o-2024-05-13"
}
```
Feel free to replace the model with newer versions of gpt-4o if needed.

### Other Keys (Optional)

Some functionalities, such as using web-search requires an API key for Bing.
You can set it using:

```bash
export BING_API_KEY=xxxxxxx
```
