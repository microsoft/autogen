# Task-Centric Memory Code Samples
_(EXPERIMENTAL, RESEARCH IN PROGRESS)_

<p align="right">
  <img src="../../packages/autogen-ext/imgs/task_centric_memory.png" alt="Description" width="300" align="right" style="margin-left: 10px;">
</p>

This directory contains code samples that illustrate the following forms of fast, memory-based learning:
* Direct memory storage and retrieval
* Learning from user advice and corrections
* Learning from user demonstrations
* Learning from the agent's own experience

Each sample connects task-centric memory to a selectable agent with no changes to that agent's code.
See the block diagram to the right for an overview of the components and their interactions.

Each sample is contained in a separate python script, using data and configs stored in yaml files for easy modification.
Note that since agent behavior is non-deterministic, results will vary between runs.

To watch operations live in a browser and see how task-centric memory works,
open the HTML page at the location specified at the top of the config file,
such as: `./pagelogs/teachability/0  Call Tree.html`
To turn off logging entirely, set logging level to NONE in the config file.

The config files specify an _AssistantAgent_ by default, which uses a fixed, multi-step system prompt.
To use _MagenticOneGroupChat_ instead, specify that in the yaml file where indicated.


## Installation

Install AutoGen and its extension package as follows:

```bash
pip install -U "autogen-agentchat" "autogen-ext[openai]" "autogen-ext[task-centric-memory]"
```

Assign your OpenAI key to the environment variable OPENAI_API_KEY,
or else modify `utils/client.py` as appropriate for the model you choose.


## Running the Samples

The following samples are listed in order of increasing complexity.
Execute the corresponding commands from this (autogen_ext/task_centric_memory) directory.


### Making AssistantAgent Teachable

This short, interactive code sample shows how to make the AssistantAgent teachable.
The following steps show the agent learning a user teaching from one chat session to the next,
starting with an empty memory bank.
The memory bank can be cleared manually by deleting the memory_bank directory (if it exists from a prior run), as shown below.
    
```bash
rm -r memory_bank
python chat_with_teachable_agent.py
Now chatting with a teachable agent. Please enter your first message. Type 'exit' or 'quit' to quit.

You: How many items should be put in research summaries?
---------- user ----------
How many items should be put in research summaries?
---------- teachable_agent ----------
<generates a long discussion>

You: Whenever asked to prepare a research summary, try to cover just the 5 top items.
---------- user ----------
Whenever asked to prepare a research summary, try to cover just the 5 top items.
---------- teachable_agent ----------
<discusses the advice>

You: quit

python chat_with_teachable_agent.py`
Now chatting with a teachable agent. Please enter your first message. Type 'exit' or 'quit' to quit.

You: How many items should be put in research summaries?
---------- user ----------
How many items should be put in research summaries?
---------- teachable_agent ----------
[MemoryContent(content='Whenever asked to prepare a research summary, try to cover just the 5 top items.', mime_type='MemoryMimeType.TEXT', metadata={})]
---------- teachable_agent ----------
<generates a more appropriate answer> 
```


### Direct Memory Storage and Retrieval

This sample shows how an app can access the `MemoryController` directly
to retrieve previously stored task-insight pairs as potentially useful examplars when solving some new task.
A task is any text instruction that the app may give to an agent.
An insight is any text (like a hint, advice, a demonstration or plan) that might help the agent perform such tasks.

A typical app will perform the following steps in some interleaved order:
1. Call the `MemoryController` repeatedly to store a set of memories (task-insight pairs).
2. Call the `MemoryController` repeatedly to retrieve any memories related to a new task.
3. Use the retrieved insights, typically by adding them to the agent's context window. (This step is not illustrated by this code sample.)

This sample code adds several task-insight pairs to memory, retrieves memories for a set of new tasks,
logs the full retrieval results, and reports the retrieval precision and recall.

`python eval_retrieval.py configs/retrieval.yaml`

Precision and recall for this sample are usually near 100%.


### Agent Learning from User Advice and Corrections

This sample first tests the agent (once) for knowledge it currently lacks.
Then the agent is given advice to help it solve the task, and the context window is cleared.
Finally the agent is once tested again to see if it can retrieve and use the advice successfully.

`python eval_teachability.py configs/teachability.yaml`

With the benefit of memory, the agent usually succeeds on this sample.


### Agent Learning from User Demonstrations

This sample asks the agent to perform a reasoning task (ten times) on which it usually fails.
The agent is then given one demonstration of how to solve a similar but different task, and the context window is cleared.
Finally the agent is tested 10 more times to see if it can retrieve and apply the demonstration to the original task.

`python eval_learning_from_demonstration.py configs/demonstration.yaml`

The agent's success rate tends to be measurably higher after the demonstration has been stored in memory.


### Agent Learning from Its Own Experience

This sample asks the agent to perform a reasoning task on which it usually fails.
Then using automatic success or failure feedback (for a verifiable task with no side-effects on the environment), 
the agent iterates through a background learning loop to find a solution, which it then stores as an insight in memory.
Finally the agent is tested again to see if it can retrieve and apply its insight to the original task,
as well as to a similar but different task as a test of generalization.

`python eval_self_teaching.py configs/self_teaching.yaml`

Using memory, the agent usually completes both tasks successfully in the second set of trials.
