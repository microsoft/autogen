# Autogen Testbed Environment

The Autogen Testbed environment is a tool for repeatedly running a set of pre-defined Autogen scenarios in a setting with tightly-controlled initial conditions. With each run, Autogen will start from a blank slate, working out what code needs to be written, and what libraries or dependencies to install. The results of each run are logged, and can be ingested by analysis or metrics scripts (see the HumanEval example later in this README). By default, all runs are conducted in freshly-initialized docker containers, providing the recommended level of consistency and safety.

This Testbed sample has been tested in, and is known to work with, Autogen versions 0.1.14 and 0.2.0

## Setup

Before you begin, you must configure your API keys for use with the Testbed. As with other Autogen applications, the Testbed will look for the OpenAI keys in a file in the current working directy, or environment variable named, OAI_CONFIG_LIST. This can be overrriden using a command-line parameter described later.

For some scenarios, additional keys may be required (e.g., keys for the Bing Search API). These can be added to an `ENV` file in the `includes` folder. A sample has been provided in ``includes/ENV.example``. Edit ``includes/ENV`` as needed.

The Testbed also requires Docker (Desktop or Engine) AND the __python docker__ library. **It will not run in codespaces**, unless you opt for native execution (with is strongly discouraged). To install Docker Desktop see [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/). To install the Python library:

``pip install docker``

## Running the Testbed

To run the Testbed, simply execute
``python run_scenarios.py scenarios/Examples``

The default is to run each scenario once. To run each scenario 10 times, use:

``python run_scenarios.py --repeat 10 scenarios/Examples ``

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
                The number of repetitions to run for each scenario (default: 1).

  -c CONFIG, --config CONFIG
                The environment variable name or path to the OAI_CONFIG_LIST (default: OAI_CONFIG_LIST).

  --requirements REQUIREMENTS
                The requirements file to pip install before running the scenario. This file must be found in
                the 'includes' directory. (default: requirements.txt)

  --native      Run the scenarios natively rather than in docker.
                NOTE: This is not advisable, and should be done with great caution.
```

## Results

By default, the Testbed stores results in a folder heirarchy with the following template:

``./results/[scenario]/[instance_id]/[repetition]``

For example, consider the following folders:

``./results/default_two_agents_gpt35/two_agent_stocks/0``
``./results/default_two_agents_gpt35/two_agent_stocks/1``

...

``./results/default_two_agents_gpt35/two_agent_stocks/9``

This folder holds the results for the ``two_agent_stocks`` instance of the ``default_two_agents_gpt35`` scenario. The ``0`` folder contains the results of the first run. The ``1`` folder contains the results of the second run, and so on. You can think of the _instance_ as mapping to a prompt, or a unique set of parameters, while the _scenario_ defines the template in which those parameters are input.

Within each folder, you will find the following files:

- *timestamp.txt*: records the date and time of the run, along with the version of the pyautogen library installed
- *console_log.txt*: all console output produced by Docker when running autogen. Read this like you would a regular console.
- *chat_completions.json*: a log of all OpenAI ChatCompletions, as logged by `autogen.ChatCompletion.start_logging(compact=False)`
- *[agent]_messages.json*: for each Agent, a log of their messages dictionaries
- *./coding*: A directory containing all code written by Autogen, and all artifacts produced by that code.

## Scenario Templating

All scenarios are stored in JSONL files (in subdirectories under `./scenarios`). Each line of a scenario file is a JSON object. The schema varies slightly based on if "template" specifies a _file_ or a _directory_.

If "template" points to a _file_, the format is:
```
{
   "id": string,
   "template": filename,
   "substitutions" {
       "find_string1": replace_string1,
       "find_string2": replace_string2,
       ...
       "find_stringN": replace_stringN
   }
}
```

For example:

```
{
    "id": "two_agent_stocks_gpt4",
    "template": "default_two_agents.py",
    "substitutions": {
        "\__MODEL\__": "gpt-4",
        "\__PROMPT\__": "Plot and save to disk a chart of NVDA and TESLA stock price YTD."
    }
}
```


If "template" points to a _directory_, the format is:

```
{
   "id": string,
   "template": dirname,
   "substitutions" {
       "filename1": {
       	   "find_string1_1": replace_string1_1,
           "find_string1_2": replace_string1_2,
           ...
           "find_string1_M": replace_string1_N
       }
       "filename2": {
       	   "find_string2_1": replace_string2_1,
           "find_string2_2": replace_string2_2,
           ...
           "find_string2_N": replace_string2_N
       }
   }
}
```

For example:

```
{
    "id": "two_agent_stocks_gpt4",
    "template": "default_two_agents",
    "substitutions": {
	"scenario.py": {
            "\__MODEL\__": "gpt-4",
	},
	"prompt.txt": {
            "\__PROMPT\__": "Plot and save to disk a chart of NVDA and TESLA stock price YTD."
        }
    }
}
```

In this example, the string `__MODEL__` will be replaced in the file `scenarios.py`, while the string `__PROMPT__` will be replaced in the `prompt.txt` file.


## Scenario Expansion Algorithm

When the Testbed runs a scenario, it creates a local folder to share with Docker. As noted above, each instance and repetition gets its own folder along the path: ``./results/[scenario]/[instance_id]/[repetition]``

For the sake of brevity we will refer to this folder as the `DEST_FOLDER`.

The algorithm for populating the `DEST_FOLDER` is as follows:

1. Recursively copy the contents of `./incudes` to DEST_FOLDER. This folder contains all the basic starter files for running a scenario, including an ENV file which will set the Docker environment variables.
2. Append the OAI_CONFIG_LIST to the ENV file so that autogen may access these secrets.
3. Recursively copy the scenario folder (if `template` in the json scenario definition points to a folder) to DEST_FOLDER. If the `template` instead points to a file, copy the file, but rename it to `scenario.py`
4. Apply any templating, as outlined in the prior section.
5. Write a run.sh file to DEST_FOLDER that will be executed by Docker when it is loaded.


## Scenario Execution Algorithm

Once the scenario has been expanded it is run (via run.sh). This script will execute the following steps:

1. Read and set the ENV environment variables
2. If a file named `global_init.sh` is present, run it.
3. If a file named `scenario_init.sh` is present, run it.
4. Install the requirements file (if running in Docker)
5. Run the Autogen scenario via `python scenario.py`
6. Clean up (delete cache, etc.)
7. If a file named `scenario_finalize.sh` is present, run it.
8. If a file named `global_finalize.sh` is present, run it.
9. echo "SCENARIO COMPLETE !#!#", signaling that all steps completed.

Notably, this means that scenarios can add custom init and teardown logic by including `scenario_init.sh` and `scenario_finalize.sh` files.


## (Example) Running HumanEval

One sample Testbed scenario type is a variation of the classic [HumanEval](https://github.com/openai/human-eval) benchmark. In this scenario, agents are given access to the unit test results, and are able to continue to debug their code until the problem is solved or they run out of tokens or turns. We can then count how many turns it took to solve the problem (returning -1 if the problem remains unsolved by the end of the conversation, and "" if the run is missing).

Accessing this scenario-type requires downloading and converting the HumanEval dataset, running the Testbed, collating the results, and finally computing the metrics. The following commands will accomplish this, running each test instance 3 times with GPT-3.5-Turbo-16k:

```
python utils/download_humaneval.py
python ./run_scenarios.py scenarios/HumanEval/human_eval_two_agents_gpt35.jsonl
python utils/collate_human_eval.py ./results/human_eval_two_agents_gpt35 | python utils/metrics_human_eval.py > human_eval_results_gpt35.csv
cat human_eval_results_gpt35.csv
```

## (Example) Running GAIA

The Testbed can also be used to run the recently released [GAIA benchmark](https://huggingface.co/gaia-benchmark). This integration is presently experimental, and needs further validation. In this scenario, agents are presented with a series of questions that may include file references, or multi-modal input. Agents then must provide a `FINAL ANSWER`, which is considered correct if it (nearly) exactly matches an unambiguously accepted answer.

Accessing this scenario-type requires downloading and converting the GAIA dataset, running the Testbed, collating the results, and finally computing the metrics. The following commands will accomplish this, running each test instance once with GPT-4:

```
# Clone the GAIA dataset repo (assuming a 'repos' folder in your home directory)
cd ~/repos
git clone https://huggingface.co/datasets/gaia-benchmark/GAIA

# Expand GAIA
cd ~/repos/autogen/samples/tools/testbed
python ./utils/expand_gaia.py ~/repos/GAIA

# Run GAIA
python ./run_scenarios.py ./scenarios/GAIA/gaia_validation_level_1__two_agents_gpt4.jsonl

# Compute Metrics
python utils/collate_gaia_csv.py ./results/gaia_validation_level_1__two_agents_gpt4 | python utils/metrics_gaia.py
```
