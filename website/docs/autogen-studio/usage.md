# Using AutoGen Studio

AutoGen Studio supports the declarative creation of an agent workflow and tasks can be specified and run in a chat interface for the agents to complete. The expected usage behavior is that developers can create skills and models, _attach_ them to agents, and compose agents into workflows that can be tested interactively in the chat interface.

## Building an Agent Workflow

AutoGen Studio implements several entities that are ultimately composed into a workflow.

### Skills

A skill is a python function that implements the solution to a task. In general, a good skill has a descriptive name (e.g. generate*images), extensive docstrings and good defaults (e.g., writing out files to disk for persistence and reuse). Skills can be \_associated with* or _attached to_ agent specifications.

![AutoGen Studio Skill Interface](./img/skill.png)

### Models

A model refers to the configuration of an LLM. Similar to skills, a model can be attached to an agent specification.
The AutoGen Studio interface supports multiple model types including OpenAI models (and any other model endpoint provider that supports the OpenAI endpoint specification), Azure OpenAI models and Gemini Models.

![AutoGen Studio Create new model](./img/model_new.png)
![AutoGen Studio Create new model](./img/model_openai.png)

### Agents

An agent entity declaratively specifies properties for an AutoGen agent (mirrors most but not all of the members of a base AutoGen Conversable agent class). Currently `UserProxyAgent` and `AssistantAgent` and `GroupChat` agent abstractions are supported.

![AutoGen Studio Create new agent](./img/agent_new.png)
![AutoGen Studio Createan assistant agent](./img/agent_groupchat.png)

Once agents have been created, existing models or skills can be _added_ to the agent.

![AutoGen Studio Add skills and models to agent](./img/agent_skillsmodel.png)

### Workflows

An agent workflow is a specification of a set of agents (team of agents) that can work together to accomplish a task. AutoGen Studio supports two types of high level workflow patterns:

#### Autonomous Chat :

This workflow implements a paradigm where agents are defined and a chat is initiated between the agents to accomplish a task. AutoGen simplifies this into defining an `initiator` agent and a `receiver` agent where the receiver agent is selected from a list of previously created agents. Note that when the receiver is a `GroupChat` agent (i.e., contains multiple agents), the communication pattern between those agents is determined by the `speaker_selection_method` parameter in the `GroupChat` agent configuration.

![AutoGen Studio Autonomous Chat Workflow](./img/workflow_chat.png)

#### Sequential Chat

This workflow allows users to specify a list of `AssistantAgent` agents that are executed in sequence to accomplish a task. The runtime behavior here follows the following pattern: at each step, each `AssistantAgent` is _paired_ with a `UserProxyAgent` and chat initiated between this pair to process the input task. The result of this exchange is summarized and provided to the next `AssistantAgent` which is also paired with a `UserProxyAgent` and their summarized result is passed to the next `AssistantAgent` in the sequence. This continues until the last `AssistantAgent` in the sequence is reached.

![AutoGen Studio Sequential Workflow](./img/workflow_sequential.png)

<!-- ```
Plot a chart of NVDA and TESLA stock price YTD. Save the result to a file named nvda_tesla.png
```

The agent workflow responds by _writing and executing code_ to create a python program to generate the chart with the stock prices.

> Note than there could be multiple turns between the `AssistantAgent` and the `UserProxyAgent` to produce and execute the code in order to complete the task.

![ARA](./img/ara_stockprices.png)

> Note: You can also view the debug console that generates useful information to see how the agents are interacting in the background. -->

<!-- - Build: Users begin by constructing their workflows. They may incorporate previously developed skills/models into agents within the workflow. User's can immediately test their workflows in the the same view or in a saved session in the playground.

- Playground: Users can start a new session, select an agent workflow, and engage in a "chat" with this agent workflow. It is important to note the significant differences between a traditional chat with a Large Language Model (LLM) and a chat with a group of agents. In the former, the response is typically a single formatted reply, while in the latter, it consists of a history of conversations among the agents.

## Entities and Concepts -->

## Testing an Agent Workflow

AutoGen Studio allows users to interactively test workflows on tasks and review resulting artifacts (such as images, code, and documents).

![AutoGen Studio Test Workflow](./img/workflow_test.png)

Users can also review the “inner monologue” of agent workflows as they address tasks, and view profiling information such as costs associated with the run (such as number of turns, number of tokens etc.), and agent actions (such as whether tools were called and the outcomes of code execution).

![AutoGen Studio Profile Workflow Results](./img/workflow_profile.png)

## Exporting Agent Workflows

Users can download the skills, agents, and workflow configurations they create as well as share and reuse these artifacts. AutoGen Studio also offers a seamless process to export workflows and deploy them as application programming interfaces (APIs) that can be consumed in other applications deploying workflows as APIs.

### Export Workflow

AutoGen Studio allows you to export a selected workflow as a JSON configuration file.

Build -> Workflows -> (On workflow card) -> Export

![AutoGen Studio Export Workflow](./img/workflow_export.png)

### Using AutoGen Studio Workflows in a Python Application

An exported workflow can be easily integrated into any Python application using the `WorkflowManager` class with just two lines of code. Underneath, the WorkflowManager rehydrates the workflow specification into AutoGen agents that are subsequently used to address tasks.

```python

from autogenstudio import WorkflowManager
# load workflow from exported json workflow file.
workflow_manager = WorkflowManager(workflow="path/to/your/workflow_.json")

# run the workflow on a task
task_query = "What is the height of the Eiffel Tower?. Dont write code, just respond to the question."
workflow_manager.run(message=task_query)

```

### Deploying AutoGen Studio Workflows as APIs

The workflow can be launched as an API endpoint from the command line using the autogenstudio commandline tool.

```bash
autogenstudio serve --workflow=workflow.json --port=5000
```

Similarly, the workflow launch command above can be wrapped into a Dockerfile that can be deployed on cloud services like Azure Container Apps or Azure Web Apps.
