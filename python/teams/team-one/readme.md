# Team-One
Team-One is a multi-agent system that utilizes a combination of five agents, including LLM and tool-based agents, to tackle intricate tasks. These tasks often involve multi-step planning and actions. 

> *Example*: Suppose a user requests to conduct a survey of AI safety papers published in the last month and create a concise presentation on the findings. Team-One will use the following process to handle this task. The orchestrator agent will break down the task into subtasks and assign them to the appropriate agents. Such as the web surfer agent to search for AI safety papers, the file surfer agent to extract information from the papers, the coder agent to create the presentation, and the computer terminal agent to execute the code. The orchestrator agent will coordinate the agents, monitor progress, and ensure the task is completed successfully.


Team-One uses agents with the following personas and capabilities:

- Orchestrator: The orchestrator agent is responsible for planning, managing subgoals, and coordinating the other agents. It can break down complex tasks into smaller subtasks and assign them to the appropriate agents. It also keeps track of the overall progress and takes corrective actions if needed (such as reassigning tasks or replanning when stuck).

- Coder: The coder agent is skilled in programming languages and is responsible for writing code.

- Computer Terminal: The computer terminal agent acts as the interface that can execute code written by the coder agent.

- File Surfer: The file surfer agent specializes in navigating files such as pdfs, powerpoints, WAV files, and other file types. It can search, read, and extract information from files.

- Web Surfer: The web surfer agent is proficient is responsible for web-related tasks. It can browse the internet, retrieve information from websites, and interact with web-based applications. It can handle interactive web pages, forms, and other web elements.


## Table of Definitions:

| Term          | Definition                                      |
|---------------|-------------------------------------------------|
| Agent         | A component that can (autonomously) act based on observations. Different agents may have different functions and actions. |
| Planning      | The process of determining actions to achieve goals, performed by the Orchestrator agent in Team-One. |
| Ledger        | A record-keeping component used by the Orchestrator agent to track the progress and manage subgoals in Team-One. |
| Stateful Tools | Tools that maintain state or data, such as the web browser and markdown-based file browser used by Team-One. |
| Tools         | Resources used by Team-One for various purposes, including stateful and stateless tools. |
| Stateless Tools | Tools that do not maintain state or data, like the commandline executor used by Team-One. |



## Capabilities and Performance
### Capabilities

- Planning: The Orchestrator agent in Team-One excels at performing planning tasks. Planning involves determining actions to achieve goals. The Orchestrator agent breaks down complex tasks into smaller subtasks and assigns them to the appropriate agents.

- Ledger: The Orchestrator agent in Team-One utilizes a ledger, which is a record-keeping component. The ledger tracks the progress of tasks and manages subgoals. It allows the Orchestrator agent to monitor the overall progress of the system and take corrective actions if needed.

- Acting in the Real World: Team-One is designed to take action in the real world based on observations. The agents in Team-One can autonomously perform actions based on the information they observe from their environment.

- Adaptation to Observation: The agents in Team-One can adapt to new observations. They can update their knowledge and behavior based on the information they receive from their environment. This allows Team-One to effectively handle dynamic and changing situations.

- Stateful Tools: Team-One utilizes stateful tools such as a web browser and a markdown-based file browser. These tools maintain state or data, which is essential for performing complex tasks that involve actions that might change the state of the environment.

- Stateless Tools: Team-One also utilizes stateless tools such as a command-line executor. These tools do not maintain state or data.

- Coding: The Coder agent in Team-One is highly skilled in programming languages and is responsible for writing code. This capability enables Team-One to create and execute code to accomplish various tasks.

- Execution of Code: The Computer Terminal agent in Team-One acts as an interface that can execute code written by the Coder agent. This capability allows Team-One to execute the code and perform actions in the system.

- File Navigation and Extraction: The File Surfer agent in Team-One specializes in navigating and extracting information from various file types such as PDFs, PowerPoints, and WAV files. This capability enables Team-One to search, read, and extract relevant information from files.

- Web Interaction: The Web Surfer agent in Team-One is proficient in web-related tasks. It can browse the internet, retrieve information from websites, and interact with web-based applications. This capability allows Team-One to handle interactive web pages, forms, and other web elements.


### Performance
Team-One currently achieves the following performance on complex agent benchmarks:

_GAIA_

| Level | Task Completion Rate* |
|-------|---------------------|
| Level 1 | 49% (26/53) |
| Level 2 | 26% (22/86) |
| Level 3 | 8% (2/26) |
| Total | 30% (50/165) |

*Indicates the percentage of tasks completed successfully on the development set.

_WebArena_

| Site           | Task Completion Rate           |
|----------------|----------------|
| Reddit         | 49%  (27/55)   |
| Shopping       | 23%  (22/96)   |
| CMS            | 16%  (16/101)  |
| Gitlab         | 41%  (32/79)   |
| Maps           | 35%  (23/65)   |
| Multiple Sites | %  (--/26)     |
| Total          | 28%  (120/422) |


# Setup


You can install the Team-One package using pip and then run the example code to see how the agents work together to accomplish a task.


1. Clone the code.
```bash
# clone agnext
cd python/teams/team-one
pip install -e .
```

2. Configure the environment variables for the chat completion client. See instructions below.


2. Now you can run the example code to see how the agents work together to accomplish a task.

```bash
python examples/example.py
```


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
