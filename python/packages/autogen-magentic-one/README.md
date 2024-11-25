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

Find additional information about Magentic-one in our [blog post](https://aka.ms/magentic-one-blog) and [technical report](https://arxiv.org/abs/2411.04468).

![](./imgs/autogen-magentic-one-example.png)

> _Example_: The figure above illustrates Magentic-One mutli-agent team completing a complex task from the GAIA benchmark. Magentic-One's Orchestrator agent creates a plan, delegates tasks to other agents, and tracks progress towards the goal, dynamically revising the plan as needed. The Orchestrator can delegate tasks to a FileSurfer agent to read and handle files, a WebSurfer agent to operate a web browser, or a Coder or Computer Terminal agent to write or execute code, respectively.

## Architecture



![](./imgs/autogen-magentic-one-agents.png)

Magentic-One work is based on a multi-agent architecture where a lead Orchestrator agent is responsible for high-level planning, directing other agents and tracking task progress. The Orchestrator begins by creating a plan to tackle the task, gathering needed facts and educated guesses in a Task Ledger that is maintained. At each step of its plan, the Orchestrator creates a Progress Ledger where it self-reflects on task progress and checks whether the task is completed. If the task is not yet completed, it assigns one of Magentic-One other agents a subtask to complete. After the assigned agent completes its subtask, the Orchestrator updates the Progress Ledger and continues in this way until the task is complete. If the Orchestrator finds that progress is not being made for enough steps, it can update the Task Ledger and create a new plan. This is illustrated in the figure above; the Orchestrator work is thus divided into an outer loop where it updates the Task Ledger and an inner loop to update the Progress Ledger.

Overall, Magentic-One consists of the following agents:
- Orchestrator: the lead agent responsible for task decomposition and planning, directing other agents in executing subtasks, tracking overall progress, and taking corrective actions as needed 
- WebSurfer: This is an LLM-based agent that is proficient in commanding and managing the state of a Chromium-based web browser. With each incoming request, the WebSurfer performs an action on the browser then reports on the new state of the web page   The action space of the WebSurfer includes navigation (e.g. visiting a URL, performing a web search);  web page actions (e.g., clicking and typing); and reading actions (e.g., summarizing or answering questions). The WebSurfer relies on the accessibility tree of the browser and on set-of-marks prompting to perform its actions.
- FileSurfer: This is an LLM-based agent that commands a markdown-based file preview application to read local files of most types. The FileSurfer can also perform common navigation tasks such as listing the contents of directories and navigating a folder structure.
- Coder: This is an LLM-based agent specialized through its system prompt for writing code, analyzing information collected from the other agents, or creating new artifacts.
- ComputerTerminal: Finally, ComputerTerminal provides the team with access to a console shell where the Coder’s programs can be executed, and where new programming libraries can be installed.

Together, Magentic-One’s agents provide the Orchestrator with the tools and capabilities that it needs to solve a broad variety of open-ended problems, as well as the ability to autonomously adapt to, and act in, dynamic and ever-changing web and file-system environments. 

While the default multimodal LLM we use for all agents is GPT-4o, Magentic-One is model agnostic and can incorporate heterogonous models to support different capabilities or meet different cost requirements when getting tasks done. For example, it can use different LLMs and SLMs and their specialized versions to power different agents. We recommend a strong reasoning model for the Orchestrator agent such as GPT-4o. In a different configuration of Magentic-One, we also experiment with using OpenAI o1-preview for the outer loop of the Orchestrator and for the Coder, while other agents continue to use GPT-4o. 


### Logging in Team One Agents

Team One agents can emit several log events that can be consumed by a log handler (see the example log handler in [utils.py](src/autogen_magentic_one/utils.py)). A list of currently emitted events are:

- OrchestrationEvent : emitted by a an [Orchestrator](src/autogen_magentic_one/agents/base_orchestrator.py) agent.
- WebSurferEvent : emitted by a [WebSurfer](src/autogen_magentic_one/agents/multimodal_web_surfer/multimodal_web_surfer.py) agent.

In addition, developers can also handle and process logs generated from the AutoGen core library (e.g., LLMCallEvent etc). See the example log handler in [utils.py](src/autogen_magentic_one/utils.py) on how this can be implemented. By default, the logs are written to a file named `log.jsonl` which can be configured as a parameter to the defined log handler. These logs can be parsed to retrieved data agent actions.

# Setup and Usage

You can install the Magentic-One package and then run the example code to see how the agents work together to accomplish a task.

1. Clone the code and install the package:

    The easiest way to install is with the [uv package installer](https://docs.astral.sh/uv/getting-started/installation/) which you need to install separately, however, this is not necessary.

    Clone repo, use uv to setup and activate virtual environment:
    ```bash
    git clone https://github.com/microsoft/autogen.git
    cd autogen/python
    uv sync  --all-extras
    source .venv/bin/activate
    ```
   For Windows, run `.venv\Scripts\activate` to activate the environment.
   
2. Install magentic-one from source:
    ```bash
    cd packages/autogen-magentic-one
    pip install -e .
    ```
    
    The following instructions are for running the example code:

3. Configure the environment variables for the chat completion client. See instructions below [Environment Configuration for Chat Completion Client](#environment-configuration-for-chat-completion-client).
4. Magentic-One code uses code execution, you need to have [Docker installed](https://docs.docker.com/engine/install/) to run any examples.
5. Magentic-One uses playwright to interact with web pages. You need to install the playwright dependencies. Run the following command to install the playwright dependencies:

```bash
playwright install --with-deps chromium
```
6. Now you can run the example code to see how the agents work together to accomplish a task.

> [!CAUTION]  
> The example code may download files from the internet, execute code, and interact with web pages. Ensure you are in a safe environment before running the example code. 

> [!NOTE]
> You will need to ensure Docker is running prior to running the example. 

  ```bash

  # Specify logs directory
  python examples/example.py --logs_dir ./logs

  # Enable human-in-the-loop mode
  python examples/example.py --logs_dir ./logs --hil_mode

  # Save screenshots of browser
  python examples/example.py --logs_dir ./logs --save_screenshots
  ```

  Arguments:

  - logs_dir: (Required) Directory for logs, downloads and screenshots of browser (default: current directory)
  - hil_mode: (Optional) Enable human-in-the-loop mode (default: disabled)
  - save_screenshots: (Optional) Save screenshots of browser (default: disabled)

7. [Preview] We have a preview API for Magentic-One. 
 You can use the `MagenticOneHelper` class to interact with the system and stream logs. See the [interface README](interface/README.md) for more details.


## Environment Configuration for Chat Completion Client

This guide outlines how to configure your environment to use the `create_completion_client_from_env` function, which reads environment variables to return an appropriate `ChatCompletionClient`.

Currently, Magentic-One only supports OpenAI's GPT-4o as the underlying LLM.

### Azure OpenAI service

To configure for Azure OpenAI service, set the following environment variables:

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

This project uses Azure OpenAI service with [Entra ID authentcation by default](https://learn.microsoft.com/azure/ai-services/openai/how-to/managed-identity). If you run the examples on a local device, you can use the Azure CLI cached credentials for testing:

Log in to Azure using `az login`, and then run the examples. The account used must have [RBAC permissions](https://learn.microsoft.com/azure/ai-services/openai/how-to/role-based-access-control) like `Azure Cognitive Services OpenAI User` for the OpenAI service; otherwise, you will receive the error: Principal does not have access to API/Operation. 

Note that even if you are the owner of the subscription, you still need to grant the necessary Azure Cognitive Services OpenAI permissions to call the API.

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

## Citation

```
@misc{fourney2024magenticonegeneralistmultiagentsolving,
      title={Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks}, 
      author={Adam Fourney and Gagan Bansal and Hussein Mozannar and Cheng Tan and Eduardo Salinas and Erkang and Zhu and Friederike Niedtner and Grace Proebsting and Griffin Bassman and Jack Gerrits and Jacob Alber and Peter Chang and Ricky Loynd and Robert West and Victor Dibia and Ahmed Awadallah and Ece Kamar and Rafah Hosn and Saleema Amershi},
      year={2024},
      eprint={2411.04468},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2411.04468}, 
}
```
