# Task Centric Memory

This AutoGen extension provides an implementation of task-centric memory, which we define as a
broad ability for AI agents to accomplish tasks more effectively by learning quickly and continually (over the long term).
This is distinct from what RAG or long context windows can provide.
While still under active research and development, this memory implementation
can be attached to virtually any unmodified AI agent, and is designed to enable agents that:

* Remember guidance, corrections, and demonstrations provided by users.
* Succeed more frequently on tasks after finding successful solutions to similar tasks.
* Learn and adapt quickly to changing circumstances to enable workflows that are dynamic and self-healing.

The implementation is also intended to:

* Be general purpose, unconstrained by types and schemas required by standard databases.
* Augment rather than interfere with an agent’s special capabilities, such as powerful reasoning, long-horizon autonomy, and tool handling.
* Operate in both foreground and background modes, so that an agent can discuss tasks with a user (in the foreground)
then work productively on those tasks (in the background) while the user does other things.
* Allow for fine-grained transparency and auditing of individual memories by human users or other agents.
* Allow agents to be personalized (to a single user) as well as specialized (to a subject, domain or project).
The benefits of personalization scale linearly with the number of users, but the benefits of domain specialization
can scale quadratically with the number of users working in that domain, as insights gained from interactions with one user
can benefit other users in similar situations.
* Support multiple memory banks dynamically attached to an agent at runtime.
* Enable enforcement of security boundaries at the level of individual memory banks.
* Allow users to download and port memory banks between agents and systems.

![task_centric_memory.png](../../../imgs/task_centric_memory.png)

The block diagram above outlines the key components of our baseline task-centric memory architecture,
which augments an agent or team with memory mechanisms.

The **Task Centric Memory Controller** implements the fast-learning methods described below,
and manages communication with an **Task Centric Memory Bank** containing a vector DB and associated structures.

The **Apprentice** is a minimal reference implementation that wraps the combination of memory plus some agent or team.
Certain applications will use the Apprentice,
while others will directly instantiate and call the Task Centric Memory Controller.

We’ve successfully tested task-centric memory with a simple AssistantAgent and MagenticOneGroupChat.

## Memory Creation and Storage

Each stored memory (called a _memo_) is an insight (in text form) crafted to help the agent accomplish future tasks that are similar
to some task encountered in the past. If the user provides advice for solving a given task,
the advice is extracted and stored as an insight. If the user demonstrates how to perform a task,
the task and demonstration are stored together as an insight that could be applied to similar but different tasks.
If the agent is given a task (free of side-effects) and some means of determining success or failure,
the memory controller repeats the following learning loop in the background some number of times:

1. Test the agent on the task a few times to check for a failure.
2. If a failure is found, analyze the agent’s response in order to:
   1. Diagnose the failure of reasoning or missing information,
   2. Phrase a general piece of advice, such as what a teacher might give to a student,
   3. Temporarily append this advice to the task description,
   4. Return to step 1.
   5. If some piece of advice succeeds in helping the agent solve the task a number of times, add the advice as an insight to memory.
3. For each insight to be stored in memory, an LLM is prompted to generate a set of free-form, multi-word topics related to the insight. Each topic is embedded to a fixed-length vector and stored in a vector DB mapping it to the topic’s related insight.

## Memory Retrieval and Usage

When the agent is given a task, the following steps are performed by the memory controller:
1. The task is rephrased into a generalized form.
2. A set of free-form, multi-word query topics are generated from the generalized task.
3. A potentially large number of previously stored topics, those most similar to each query topic, are retrieved from the vector DB along with the insights they map to.
4. These candidate memos are filtered by the aggregate similarity of their stored topics to the query topics.
5. In the final filtering stage, an LLM is prompted to return only those insights that seem potentially useful in solving the task at hand.

Retrieved insights that pass the filtering steps are listed under a heading like
“Important insights that may help solve tasks like this”, then appended to the task description before it is passed to the agent as usual.

## Setup and Usage

Install AutoGen and its extension package as follows:

`pip install "autogen-ext[task-centric-memory]"`

We provide [sample code](../../../../../samples/task_centric_memory) to illustrate the following forms of memory-based fast learning:
* Agent learning from user advice and corrections
* Agent learning from user demonstrations
* Agent learning from its own experience
