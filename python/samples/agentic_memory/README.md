# Agentic Memory Code Samples

This directory contains code samples that illustrate the following forms of memory-based fast learning:
* Agent learning from user advice and corrections
* Agent learning from user demonstrations    
* Agent learning from its own experience

Each sample is contained in a separate python script, using data and settings stored in yaml files.
Note that since agent behavior is non-deterministic, results will vary between runs.

To watch operations live in a browser and see how agentic memory works, 
open the HTML page at the location specified at the top of the settings file, 
such as: `~/pagelogs/teachability/0  Call Tree.html`

The settings files specify a _thin agent_ by default, which is just the model client plus a canned system prompt.
To use _MagenticOneGroupChat_ instead, specify that in the yaml file where indicated.


## Setup

After installing AutoGen-Core, install its extension package from the `autogen/python/packages/autogen-ext` directory as follows:

`pip install -e .[agentic-memory]`


## Running the Samples

Execute the following commands from this (autogen_ext/agentic_memory) directory.


### Agent Learning from User Advice and Corrections

This sample first tests the agent for knowledge it currently lacks.
Then the agent is given advice to help it solve the task, and the context window is cleared.
Finally the agent is tested again to see if it can retrieve and use the advice successfully.

`python eval_teachability.py settings/teachability.yaml`


### Agent Learning from User Demonstrations

This sample asks the agent to perform a reasoning task on which it usually fails.
The agent is then given a demonstration of how to solve a similar but different task, and the context window is cleared.
Finally the agent is tested again to see if it can retrieve and apply the demonstration to the original task.

`python eval_learning_from_demonstration.py settings/demonstration.yaml`


### Agent Learning from Its Own Experience

This sample asks the agent to perform a reasoning task on which it usually fails.
Then the agent (running in the background) iterates through a learning loop in an effort to find a solution, 
which it then stores as an insight in memory.
Finally the agent is tested again to see if it can retrieve and apply the insight to the original task,
as well as to a similar but different task.

`python eval_self_teaching.py settings/self_teaching.yaml`
