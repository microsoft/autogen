# GAIA Benchmark

This scenario implements the [GAIA](https://arxiv.org/abs/2311.12983) agent benchmark.

## Running the TwoAgents tasks

Level 1 tasks:
```sh
autogenbench run Tasks/gaia_test_level_1__two_agents.jsonl
autogenbench tabulate Results/gaia_test_level_1__two_agents
```

Level 2 and 3 tasks are executed similarly.

## Running the SocietyOfMind tasks

Running the SocietyOfMind tasks is similar to the TwoAgentTasks, but requires an `ENV.json` file
with a working BING API key. This file should be located in the root current working directory
from where you are running autogenbench, and should have at least the following contents:

```json
{
    "BING_API_KEY": "Your_API_key"
}
```

Once created, simply run:

```sh
autogenbench run Tasks/gaia_test_level_1__soc.jsonl
autogenbench tabulate Results/gaia_test_level_1__soc
```

And similarly for level 2 and 3.

## References
**GAIA: a benchmark for General AI Assistants**<br/>
Grégoire Mialon, Clémentine Fourrier, Craig Swift, Thomas Wolf, Yann LeCun, Thomas Scialom<br/>
[https://arxiv.org/abs/2311.12983](https://arxiv.org/abs/2311.12983)
