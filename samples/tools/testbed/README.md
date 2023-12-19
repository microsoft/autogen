# AutoGenBench

AutoGenBench is a tool for repeatedly running a set of pre-defined AutoGen scenarios in a setting with tightly-controlled initial conditions. With each run, AutoGen will start from a blank slate, working out what code needs to be written, and what libraries or dependencies to install. The results of each run are logged, and can be ingested by analysis or metrics scripts (see the HumanEval example later in this README). By default, all runs are conducted in freshly-initialized docker containers, providing the recommended level of consistency and safety.

AutoGenBench is known to work with, all AutoGen 0.1.*, and 0.2.* versions.

## Installation and Setup

**To get the most out of AutoGenBench, the `autogenbench` package should be installed**. At present, the best way to do this is to git clone the [autogen](https://github.com/microsoft/autogen) repository then from the repository root, execute:

```
pip install -e samples/tools/testbed
```

or, from within the `samples/tools/testbed` folder (e.g., if reading this README):

```
pip install -e .
```

After installation, you must configure your API keys. As with other AutoGen applications, AutoGenBench will look for the OpenAI keys in the OAI_CONFIG_LIST file in the current working directory, or the OAI_CONFIG_LIST environment variable. If neither are provided, it will user the environment variable OPENAI_API_KEY. This behavior can be overridden using a command-line parameter described later.

For some scenarios, additional keys may be required (e.g., keys for the Bing Search API). These can be added to an `ENV.json` file in the current working folder. An example `ENV.json` file is provided below:

```
{
    "BING_API_KEY": "xxxyyyzzz"
}
```

AutoGenBench also requires Docker (Desktop or Engine). **It will not run in GitHub codespaces**, unless you opt for native execution (with is strongly discouraged). To install Docker Desktop see [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/).


## Cloning Benchmarks
To clone an existing benchmark, simply run:
```
autogenbench clone [BENCHMARK]
```

For example,

```
autogenbench clone HumanEval
```

To see which existing benchmarks are available to clone, run:

```
autogenbench clone --list
```

## Running AutoGenBench

To run a benchmark (which executes the tasks, but does not compute metrics), simply execute:
```
cd [BENCHMARK]
autogenbench run Tasks
```

For example,
```
cd HumanEval
autogenbench run Tasks
```

The default is to run each task once. To run each scenario 10 times, use:

```
autogenbench run --repeat 10 Tasks
```

The `autogenbench` command-line tool allows a number of command-line arguments to control various parameters of execution. Type ``autogenbench -h`` to explore these options:

```
'autogenbench run' will run the specified autogen scenarios for a given number of repetitions and record all logs and trace information. When running in a Docker environment (default), each run will begin from a common, tightly controlled, environment. The resultant logs can then be further processed by other scripts to produce metrics.

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
                The requirements file to pip install before running the scenario.

  -d DOCKER_IMAGE, --docker-image DOCKER_IMAGE
                The Docker image to use when running scenarios. Can not be used together with --native.
                (default: 'autogen/testbed:default', which will be created if not present)

  -d DOCKER_IMAGE, --docker-image DOCKER_IMAGE
                The Docker image to use when running scenarios. Can not be used together with --native.
                (default: 'autogen/testbed:default', which will be created if not present)

  --native      Run the scenarios natively rather than in docker.
                NOTE: This is not advisable, and should be done with great caution.
```

## Results

By default, the AutoGenBench stores results in a folder hierarchy with the following template:

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

When AutoGenBench runs a scenario, it creates a local folder to share with Docker. As noted above, each instance and repetition gets its own folder along the path: ``./results/[scenario]/[instance_id]/[repetition]``

For the sake of brevity we will refer to this folder as the `DEST_FOLDER`.

The algorithm for populating the `DEST_FOLDER` is as follows:

1. Pre-populate DEST_FOLDER with all the basic starter files for running a scenario.
2. Recursively copy the scenario folder (if `template` in the json scenario definition points to a folder) to DEST_FOLDER. If the `template` instead points to a file, copy the file, but rename it to `scenario.py`
3. Apply any templating, as outlined in the prior section.
4. Write a run.sh file to DEST_FOLDER that will be executed by Docker when it is loaded.


## Scenario Execution Algorithm

Once the scenario has been expanded it is run (via run.sh). This script will execute the following steps:

1. If a file named `global_init.sh` is present, run it.
2. If a file named `scenario_init.sh` is present, run it.
3. Install the requirements file (if running in Docker)
4. Run the Autogen scenario via `python scenario.py`
5. Clean up (delete cache, etc.)
6. If a file named `scenario_finalize.sh` is present, run it.
7. If a file named `global_finalize.sh` is present, run it.
8. echo "SCENARIO COMPLETE !#!#", signaling that all steps completed.

Notably, this means that scenarios can add custom init and teardown logic by including `scenario_init.sh` and `scenario_finalize.sh` files.
