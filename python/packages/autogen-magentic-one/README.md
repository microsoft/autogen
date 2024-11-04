# Magentic-One


> [!CAUTION]
> Computer use is a beta feature. Please be aware that computer use poses unique risks that are distinct from standard API features or chat interfaces. These risks are heightened when using computer use to interact with the internet. To minimize risks, consider taking precautions such as:
>
> 1. Use a dedicated virtual machine or container with minimal privileges to prevent direct system attacks or accidents.
> 2. Avoid giving the model access to sensitive data, such as account login information, to prevent information theft.
> 3. Limit internet access to an allowlist of domains to reduce exposure to malicious content.
> 4. Ask a human to confirm decisions that may result in meaningful real-world consequences as well as any tasks requiring affirmative consent, such as accepting cookies, executing financial transactions, or agreeing to terms of service.
>
> In some circumstances, Claude will follow commands found in content even if it conflicts with the user's instructions. For example, instructions on webpages or contained in images may override user instructions or cause Claude to make mistakes. We suggest taking precautions to isolate Claude from sensitive data and actions to avoid risks related to prompt injection.
>
> Finally, please inform end users of relevant risks and obtain their consent prior to enabling computer use in your own products.

Magentic-One is a generalist multi-agent softbot that utilizes a combination of five agents, including LLM and tool-based agents, to tackle intricate tasks. For example, it can be used to solve general tasks that involve multi-step planning and action in the real-world.

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

# Setup

You can install the Magentic-One package using pip and then run the example code to see how the agents work together to accomplish a task.

1. Clone the code.

```bash
git clone -b staging https://github.com/microsoft/autogen.git
cd autogen/python/packages/autogen-magentic-one
pip install -e .
```

2. Configure the environment variables for the chat completion client. See instructions below.
3. Now you can run the example code to see how the agents work together to accomplish a task.

**NOTE:** The example code may download files from the internet, execute code, and interact with web pages. Ensure you are in a safe environment before running the example code.



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

4. [Preview] We have a preview API for Magentic-One. 
 You can use the `MagenticOneHelper` class to interact with the system. See the [interface README](interface/README.md) for more details.


## Environment Configuration for Chat Completion Client

This guide outlines how to configure your environment to use the `create_completion_client_from_env` function, which reads environment variables to return an appropriate `ChatCompletionClient`.

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

### Other Keys

Some functionalities, such as using web-search requires an API key for Bing.
You can set it using:

```bash
export BING_API_KEY=xxxxxxx
```
