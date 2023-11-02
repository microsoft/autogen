# Autogen Testbed Environment

The Autogen Testbed environment is a tool for repeatedly running a set of pre-defined Autogen scenarios in a setting with tightly-controlled initial conditions. With each run, Autogen will start from a blank slate, working out what code needs to be written, and what libraries or dependencies to install. The results of each run are logged, and can be ingested by analysis or metrics scripts. By default, all runs are conducted in freshly-initialized docker containers, providing the recommended level of consistency and safety.

## Setup

Before you begin, you must configure your API keys for use with the Testbed. These keys extend beyond those typically found in an OAI_CONFIG_LIST, and can include such things as keys for the Bing Search API or other services used by the scenarios. There is an example ENV file in ``includes/ENV.example``. To get started:

``cp includes/ENV.example includes/ENV``

Then edit ``includes/ENV`` as needed.

The Testbed also requires installation of the __python docker__ library:

``pip install docker``

## Running the Testbed

To run the Testbed, simply execute
``python run_scenarios.py``

The default it to repeat this scenario 10 times. This can be costly. To run each scenario only once, use:
``python run_scenarios.py --repeat 1``


The run_scenarios.py script also allows a number of command-line arguments to control various parameters of execution. Type ``python run_scenarios.py -h`` to explore these options:

```
run_scenarios.py will run the specified autogen scenarios for a given number of repetitions and record all logs and trace information. When running in a Docker environment (default), each run will begin from a common, tightly controlled, environment. The resultant logs can then be further processed by other scripts to produce metrics.

positional arguments:
  scenario      The JSONL scenario file to run. If a directory is specified,
                then all JSONL scenarios in the directory are run. (default:
                ./scenarios)

options:
  -h, --help    show this help message and exit

  -r REPEAT, --repeat REPEAT
                The number of repetitions to run for each scenario (default: 10).

  --native      Run the scenarios natively rather than in docker.
                NOTE: This is not advisable, and should be done with great caution.
```

## Results

By default, the Testbed stores results in a folder heirarchy with the following template:

``./results/[scenario]/[instance_id]/[repetition]``

For example, consider the following folders:

``./results/default_two_agents/two_agent_stocks_gpt4/0``
``./results/default_two_agents/two_agent_stocks_gpt4/1``

...

``./results/default_two_agents/two_agent_stocks_gpt4/9``

This folder holds the results for the ``two_agent_stocks_gpt4`` instance of the ``default_two_agents`` scenario. The ``0`` folder contains the results of the first run. The ``1`` folder contains the results of the second run, and so on. You can think of the _instance_ as mapping to a prompt, or a unique set of parameters, while the _scenario_ defines the template in which those parameters are input.

Within each folder, you will find the following files:

- *timestamp.txt*: records the date and time of the run, along with the version of the pyautogen library installed
- *console_log.txt*: all console output produced by Docker when running autogen. Read this like you would a regular console.
- *chat_completions.json*: a log of all OpenAI ChatCompletions, as logged by ``autogen.ChatCompletion.start_logging(compact=False)``
- *[agent]_messages.json*: for each Agent, a log of their messages dictionaries
- *./coding*: A directory containing all code written by Autogen, and all artifacts produced by that code.

## Scenario Templating

All scenarios are stored in JSONL files in the ``./scenarios'' directory. Each line of a scenario file is a JSON object with the following schema:

```
{
   "id": string,
   "template": filename,
   "values" {
       "field_name1": string,
       "field_name2": string,
       ...
       "field_nameN": string
   }
}
```

For example:

```
{
    "id": "two_agent_stocks_gpt4",
    "template": "default_two_agents.py",
    "values": {
        "\__MODEL\__": "gpt-4",
        "\__PROMPT\__": "Plot and save to disk a chart of NVDA and TESLA stock price YTD."
    }
}
```

Where the ``id`` is the instance id used when saving results, ``template`` points to a python file that contains the scenario logic, and ``values`` contains a set of strings to find and replace when expanding the template.

An example templated python file is:

```
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
import os
import json
import testbed_utils

testbed_utils.init()
##############################

config_list = config_list_from_json(
        "OAI_CONFIG_LIST", filter_dict={"model": ["\__MODEL\__"]},
)

assistant = AssistantAgent("assistant", llm_config={
    "request_timeout": 180,
    "config_list": config_list}
)
user_proxy = UserProxyAgent("user_proxy",
            human_input_mode="NEVER",
            code_execution_config={
                "work_dir": "coding",
                "use_docker": False,
            },
            max_consecutive_auto_reply=10)
user_proxy.initiate_chat(assistant, message="\__PROMPT\__")


##############################
testbed_utils.finalize(assistant, user_proxy)
```


## Running HumanEval

One sample Testbed scenario type is a variation of the classic [HumanEval](https://github.com/openai/human-eval) benchmark. In this scenario, agents are given access to the unit test results, and are able to continue to debug their code until the problem is solved or they run out of tokens or turns. We can then count how many turns it took to solve the problem (returning -1 if the problem remains unsolved by the end of the conversation).

Accessing this scenario-type requires downloading and converting the datasets, running the Testbed, and finally collating the results. The following commands will accomplish this, running each test instance 3 times with GPT-3.5-Turbo-16k:

```
python utils/download_humaneval.py
python ./run_scenarios.py --repeat 3 scenarios/human_eval_two_agents_gpt35.jsonl
python utils/collate_human_eval.py ./results/human_eval_two_agents_gpt35 > human_eval_two_agents_gpt35_results.csv && cat human_eval_two_agents_gpt35_results.csv
```
