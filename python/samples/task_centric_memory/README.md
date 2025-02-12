# Task-Centric Memory Code Samples

This directory contains code samples that illustrate the following forms of memory-based fast learning:
* Agent learning from user advice and corrections
* Agent learning from user demonstrations
* Agent learning from its own experience

Each sample is contained in a separate python script, using data and configs stored in yaml files.
Note that since agent behavior is non-deterministic, results will vary between runs.

To watch operations live in a browser and see how task-centric memory works,
open the HTML page at the location specified at the top of the config file,
such as: `~/pagelogs/teachability/0  Call Tree.html`

The config files specify a _SimpleAgent_ by default, which is an `AssistantAgent` with a fixed system prompt.
To use _MagenticOneGroupChat_ instead, specify that in the yaml file where indicated.


## Setup

Install AutoGen and its extension package as follows:

`pip install "autogen-ext[task-centric-memory]"`

Assign your OpenAI key to the environment variable OPENAI_API_KEY,
or else modify `utils/client.py` as appropriate for the model you choose.


## Running the Samples

Execute the following commands from this (autogen_ext/task_centric_memory) directory.


### Direct Memory Access

This sample shows how an app can access the `TaskCentricMemoryController` directly
to retrieve previously stored task-insight pairs as potentially useful examples when solving some new task.
A task is any text instruction that the app may give to the agent or model client, which the app must create.
An insight is any text (like advice, a hint, a demonstration or plan) that might help the agent perform related tasks.

A typical app will perform the following steps in some interleaved order:
1. Call the `TaskCentricMemoryController` repeatedly to store a set of task-insight pairs.
2. Call the `TaskCentricMemoryController` repeatedly to retrieve any related insights for a potentially new task.
3. Use the retrieved insights, typically by adding them to the agent's context window.

This sample code adds several task-insight pairs to memory, then retrieves stored pairs for a set of new tasks,
logs the full retrieval results, and reports the percentage of successful retrievals,
where retrieving too much or too little is considered a failure.

`python direct_memory_access.py configs/direct.yaml`

The retrieval success rate for this sample is usually near 100%.

This sample does not perform step 3 (using the retrieved insights),
because that and other steps are automated by the `Apprentice` class, which is used in the following samples.


### Agent Learning from User Advice and Corrections

This sample first tests the agent (once) for knowledge it currently lacks.
Then the agent is given advice to help it solve the task, and the context window is cleared.
Finally the agent is once tested again to see if it can retrieve and use the advice successfully.

`python eval_teachability.py configs/teachability.yaml`

By using memory on this example, the agent nearly always succeeds on the second test.


### Agent Learning from User Demonstrations

This sample asks the agent to perform a reasoning task (ten times) on which it usually fails.
The agent is then given a demonstration of how to solve a similar but different task, and the context window is cleared.
Finally the agent is tested 10 more times to see if it can retrieve and apply the demonstration to the original task.

`python eval_learning_from_demonstration.py configs/demonstration.yaml`

By using memory on this example, the agent's success rate is usually higher on the second set of tests.


### Agent Learning from Its Own Experience

This sample asks the agent to perform a reasoning task on which it usually fails.
Then the agent (running in the background) iterates through a learning loop in an effort to find a solution,
which it then stores as an insight in memory.
Finally the agent is tested again to see if it can retrieve and apply the insight to the original task,
as well as to a similar but different task to test generalization.

`python eval_self_teaching.py configs/self_teaching.yaml`

By using memory on this example, the agent usually completes both tasks successfully in the second set of tests.
