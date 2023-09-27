## A5: Dynamic Group Chat


### Demonstration

- [Dynamic Group Chat](../../notebook/agentchat_groupchat.ipynb) with a product manager, a coder, and a human adm.

- [Dynamic Group Chat for a visualization task](../../notebook/agentchat_groupchat_vis.ipynb)

- [Dynamic Group Chat for a research task](../../notebook/agentchat_groupchat_research.ipynb)


### Pilot Study on the Speaker Selection Policy

To validate the necessity of multi-agent dynamic group chat and the effectiveness of the role-play speaker selection policy, we conduct a pilot study comparing a four-agent dynamic group chat system with two possible alternatives across 12 manually crafted complex [tasks](tasks.txt). Then we evaluate the performance of the three systems in terms of success rate (higher the better), average llm call (lower the better), and termination failure count (lower the better). The results show that the four-agent dynamic group chat system outperforms the other two systems in all three metrics.

#### How to run the code
1. Install dependency locally
2. Set up OpenAI model and key in [OAI_CONFIG_LIST](OAI_CONFIG_LIST.json)
3. Run `run_experiment.py`
```
python /path/to/run_experiment.py
```

#### A Four-agent dynamic group chat system
The four-agent group chat system was composed of the following group members: a user proxy to take human inputs, an engineer to write code and fix bugs, a critic to review code and provide feedback, and a code executor for executing code.

#### Two alternative systems
The first alternative system was a two-agent group chat system composed of a user proxy and an engineer. The second alternative system was a four-agent group chat system composed of the same four group members as the four-agent dynamic group chat system and a different, task-style speaker selection policy.

#### Results
#####  Number of successes on the 12 tasks (higher the better).

| Model | Two Agent | Group Chat with roleplay policy | Group Chat with task-based policy |
| --- | --- | --- | --- |
| GPT-3.5-turbo | 8 | 9 | 7 |
| GPT-4 | 9 | 11 | 8 |

##### Average number of llm calls (lower the better) and number of termination failures (lower the better) on the 12 tasks.

| Model | Two Agent | Group Chat with roleplay policy | Group Chat with task-based policy |
| --- | --- | --- | --- |
| GPT-3.5-turbo | 9.9, 9 | 5.3, 0 | 4, 0 |
| GPT-4 | 6.8, 3 | 4.5, 0 | 4, 0 |
