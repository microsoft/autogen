# Magentic-One
Magentic-One is a generalist multi-agent softbot that utilizes a combination of five agents, including LLM and tool-based agents, to tackle intricate tasks. For example, it can be used to solve general tasks that involve multi-step planning and action in the real-world.

> *Example*: Suppose a user requests to conduct a survey of AI safety papers published in the last month and create a concise presentation on the findings. Magentic-One will use the following process to handle this task. The orchestrator agent will break down the task into subtasks and assign them to the appropriate agents. Such as the web surfer agent to search for AI safety papers, the file surfer agent to extract information from the papers, the coder agent to create the presentation, and the computer terminal agent to execute the code. The orchestrator agent will coordinate the agents, monitor progress, and ensure the task is completed successfully.



## Architecture

<center>
<img src="./imgs/autogen-magentic-one-landing.png" alt="drawing" style="width:350px;"/>
</center>



Magentic-One uses agents with the following personas and capabilities:

- Orchestrator: The orchestrator agent is responsible for planning, managing subgoals, and coordinating the other agents. It can break down complex tasks into smaller subtasks and assign them to the appropriate agents. It also keeps track of the overall progress and takes corrective actions if needed (such as reassigning tasks or replanning when stuck).

- Coder: The coder agent is skilled in programming languages and is responsible for writing code.

- Computer Terminal: The computer terminal agent acts as the interface that can execute code written by the coder agent.

- Web Surfer: The web surfer agent is proficient is responsible for web-related tasks. It can browse the internet, retrieve information from websites, and interact with web-based applications. It can handle interactive web pages, forms, and other web elements.

- File Surfer: The file surfer agent specializes in navigating files such as pdfs, powerpoints, WAV files, and other file types. It can search, read, and extract information from files.

We created Magentic-One with one agent of each type because their combined abilities help tackle tough benchmarks. By splitting tasks among different agents, we keep the code simple and modular, like in object-oriented programming. This also makes each agent's job easier since they only need to focus on specific tasks. For example, the websurfer agent only needs to navigate webpages and doesn't worry about writing code, making the team more efficient and effective.


### Planning and Tracking Task Progress
<center>
<img src="./imgs/autogen-magentic-one-arch.png" alt="drawing" style="width:600px;"/>
</center>

The figure illustrates the workflow of an orchestrator managing a multi-agent setup, starting with an initial prompt or task. The orchestrator creates or updates a ledger with gathered information, including verified facts, facts to look up, derived facts, and educated guesses. Using this ledger, a plan is derived, which consists of a sequence of steps and task assignments for the agents. Before execution, the orchestrator clears the agents' contexts to ensure they start fresh. The orchestrator then evaluates if the request is fully satisfied. If so, it reports the final answer or an educated guess.

If the request is not fully satisfied, the orchestrator assesses whether the work is progressing or if there are significant barriers. If progress is being made, the orchestrator orchestrates the next step by selecting an agent and providing instructions. If the process stalls for more than two iterations, the ledger is updated with new information, and the plan is adjusted. This cycle continues, iterating through steps and evaluations, until the task is completed. The orchestrator ensures organized, effective tracking and iterative problem-solving to achieve the prompt's goal.

Note that many parameters such as terminal logic and maximum number of stalled iterations are configurable. Also note that the orchestrator cannot instantiate new agents. This is possible but not implemented in Magentic-One.


## Table of Definitions:

| Term          | Definition                                      |
|---------------|-------------------------------------------------|
| Agent         | A component that can (autonomously) act based on observations. Different agents may have different functions and actions. |
| Planning      | The process of determining actions to achieve goals, performed by the Orchestrator agent in Magentic-One. |
| Ledger        | A record-keeping component used by the Orchestrator agent to track the progress and manage subgoals in Magentic-One. |
| Stateful Tools | Tools that maintain state or data, such as the web browser and markdown-based file browser used by Magentic-One. |
| Tools         | Resources used by Magentic-One for various purposes, including stateful and stateless tools. |
| Stateless Tools | Tools that do not maintain state or data, like the commandline executor used by Magentic-One. |



## Capabilities and Performance
### Capabilities

- Planning: The Orchestrator agent in Magentic-One excels at performing planning tasks. Planning involves determining actions to achieve goals. The Orchestrator agent breaks down complex tasks into smaller subtasks and assigns them to the appropriate agents.

- Ledger: The Orchestrator agent in Magentic-One utilizes a ledger, which is a record-keeping component. The ledger tracks the progress of tasks and manages subgoals. It allows the Orchestrator agent to monitor the overall progress of the system and take corrective actions if needed.

- Acting in the Real World: Magentic-One is designed to take action in the real world based on observations. The agents in Magentic-One can autonomously perform actions based on the information they observe from their environment.

- Adaptation to Observation: The agents in Magentic-One can adapt to new observations. They can update their knowledge and behavior based on the information they receive from their environment. This allows Magentic-One to effectively handle dynamic and changing situations.

- Stateful Tools: Magentic-One utilizes stateful tools such as a web browser and a markdown-based file browser. These tools maintain state or data, which is essential for performing complex tasks that involve actions that might change the state of the environment.

- Stateless Tools: Magentic-One also utilizes stateless tools such as a command-line executor. These tools do not maintain state or data.

- Coding: The Coder agent in Magentic-One is highly skilled in programming languages and is responsible for writing code. This capability enables Magentic-One to create and execute code to accomplish various tasks.

- Execution of Code: The Computer Terminal agent in Magentic-One acts as an interface that can execute code written by the Coder agent. This capability allows Magentic-One to execute the code and perform actions in the system.

- File Navigation and Extraction: The File Surfer agent in Magentic-One specializes in navigating and extracting information from various file types such as PDFs, PowerPoints, and WAV files. This capability enables Magentic-One to search, read, and extract relevant information from files.

- Web Interaction: The Web Surfer agent in Magentic-One is proficient in web-related tasks. It can browse the internet, retrieve information from websites, and interact with web-based applications. This capability allows Magentic-One to handle interactive web pages, forms, and other web elements.


### What Magentic-One Cannot Do

- **Video Scrubbing:** The agents are unable to navigate and process video content.
- **User in the Loop Optimization:** The system does not currently incorporate ongoing user interaction beyond the initial task submission.
- **Code Execution Beyond Python or Shell:** The agents are limited to executing code written in Python or shell scripts.
- **Agent Instantiation:** The orchestrator agent cannot create new agents dynamically.
- **Session-Based Learning:** The agents do not learn from previous sessions or retain information beyond the current session.
- **Limited LLM Capacity:** The agents' abilities are constrained by the limitations of the underlying language model.
- **Web Surfer Limitations:** The web surfer agent may struggle with certain types of web pages, such as those requiring complex interactions or extensive JavaScript handling.


### Safety and Risks

**Code Execution:**
- **Risks:** Code execution carries inherent risks as it happens in the environment where the agents run using the command line executor. This means that the agents can execute arbitrary Python code.
- **Mitigation:** Users are advised to run the system in isolated environments, such as Docker containers, to mitigate the risks associated with executing arbitrary code.

**Web Browsing:**
- **Capabilities:** The web surfer agent can operate on most websites, including performing tasks like booking flights.
- **Risks:** Since the requests are sent online using GPT-4-based models, there are potential privacy and security concerns. It is crucial not to provide sensitive information such as keys or credit card data to the agents.

**Safeguards:**
- **Guardrails from LLM:** The agents inherit the guardrails from the underlying language model (e.g., GPT-4). This means they will refuse to generate toxic or stereotyping content, providing a layer of protection against generating harmful outputs.
- **Limitations:** The agents' behavior is directly influenced by the capabilities and limitations of the underlying LLM. Consequently, any lack of guardrails in the language model will also affect the behavior of the agents.

**General Recommendations:**
- Always use isolated or controlled environments for running the agents to prevent unauthorized or harmful code execution.
- Avoid sharing sensitive information with the agents to protect your privacy and security.
- Regularly update and review the underlying LLM and system configurations to ensure they adhere to the latest safety and security standards.


### Performance
Magentic-One currently achieves the following performance on complex agent benchmarks.


#### GAIA


 GAIA is a benchmark from Meta that contains complex tasks that require multi-step reasoning and tool use. For example,

> *Example*: If Eliud Kipchoge could maintain his record-making marathon pace indefinitely, how many thousand hours would it take him to run the distance between the Earth and the Moon its closest approach? Please use the minimum perigee value on the Wikipedia page for the Moon when carrying out your calculation. Round your result to the nearest 1000 hours and do not use any comma separators if necessary.

In order to solve this task, the orchestrator begins by outlining the steps needed to solve the task of calculating how many thousand hours it would take Eliud Kipchoge to run the distance between the Earth and the Moon at its closest approach. The orchestrator instructs the web surfer agent to gather Eliud Kipchoge's marathon world record time (2:01:39) and the minimum perigee distance of the Moon from Wikipedia (356,400 kilometers).

Next, the orchestrator assigns the assistant agent to use this data to perform the necessary calculations. The assistant converts Kipchoge's marathon time to hours (2.0275 hours) and calculates his speed (approximately 20.81 km/h). It then calculates the total time to run the distance to the Moon (17,130.13 hours), rounding it to the nearest thousand hours, resulting in approximately 17,000 thousand hours. The orchestrator then confirms and reports this final result.

Here is the performance of Magentic-One on a GAIA development set.

| Level   | Task Completion Rate* |
|---------|-----------------------|
| Level 1 | 55% (29/53)           |
| Level 2 | 34% (29/86)           |
| Level 3 | 12% (3/26)            |
| Total   | 37% (61/165)          |

*Indicates the percentage of tasks completed successfully on the *validation* set.

#### WebArena

> Example: Tell me the count of comments that have received more downvotes than upvotes for the user who made the latest post on the Showerthoughts forum.

To solve this task, the agents began by logging into the Postmill platform using provided credentials and navigating to the Showerthoughts forum. They identified the latest post in this forum, which was made by a user named Waoonet. To proceed with the task, they then accessed Waoonet's profile to examine the comments section, where they could find all comments made by this user.

Once on Waoonet's profile, the agents focused on counting the comments that had received more downvotes than upvotes. The web\_surfer agent analyzed the available comments and found that Waoonet had made two comments, both of which had more upvotes than downvotes. Consequently, they concluded that none of Waoonet's comments had received more downvotes than upvotes. This information was summarized and reported back, completing the task successfully.

| Site           | Task Completion Rate |
|----------------|----------------------|
| Reddit         | 54%  (57/106)        |
| Shopping       | 33%  (62/187)        |
| CMS            | 29%  (53/182)        |
| Gitlab         | 28%  (50/180)        |
| Maps           | 35%  (38/109)        |
| Multiple Sites | 15%  (7/48)          |
| Total          | 33%  (267/812)       |


### Logging in Team One Agents

Team One agents can emit several log events that can be consumed by a log handler (see the example log handler in [utils.py](src/autogen_magentic_one/utils.py)). A list of currently emitted events are:

- OrchestrationEvent : emitted by a an [Orchestrator](src/autogen_magentic_one/agents/base_orchestrator.py) agent.
- WebSurferEvent : emitted by a [WebSurfer](src/autogen_magentic_one/agents/multimodal_web_surfer/multimodal_web_surfer.py) agent.

In addition, developers can also handle and process logs generated from the AutoGen core library (e.g., LLMCallEvent etc). See  the example log handler in [utils.py](src/autogen_magentic_one/utils.py) on how this can be implemented. By default, the logs are written to a file named `log.jsonl` which can be configured as a parameter to the defined log handler. These logs can be parsed to retrieved data agent actions.


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

```bash
python examples/example_websurfer.py
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

### Other Keys
Some functionalities, such as using web-search requires an API key for Bing.
You can set it using:
```bash
export BING_API_KEY=xxxxxxx
```