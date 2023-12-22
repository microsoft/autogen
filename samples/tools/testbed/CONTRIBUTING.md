# Contributing to AutoGenBench

As part of the broader AutoGen project, AutoGenBench welcomes community contributions. Contributions are subject to AutoGen's [contribution guidelines](https://microsoft.github.io/autogen/docs/Contribute), as well as a few additional AutoGenBench-specific requirements that will be outlined here. You may also wish to develop your own private benchmark scenarios and the guidance this document will help with such efforts as well. Below you will find the general requirements, followed by detailed technical documents.

## General Contribution Requirements
We ask that all contributions to AutoGenBench adhere to the following requirements:

- Code adheres to AutoGen's broader [contribution guidelines](https://microsoft.github.io/autogen/docs/Contribute)
- Benchmarks should live in a subfolder of `/samples/tools/testbed/scenarios`, alongside `HumanEval`, `GAIA`, etc.
- Benchmark scenarios include a detailed README.md in the root of their folder, describing the benchmark, and providing citations where warranted.
- Benchmark data (tasks, ground truth examples, etc.) should be downloaded from their original source rather than hosted in AutoGen repository (unless the benchmark is original, and the reposity *is* the original source)
    - You can use the `Scripts/init_tasks.py` file to automate this download.
- Basic scoring should be compatible with the `autogenbench tabulate` command (e.g., by outputting logs compatible with the default tabulation mechanism, or by providing a  `Scripts/custom_tabulate.py` file)
- If you wish your benchmark to be compatible with the `autogenbench clone` command, include a `MANIFEST.json` file in the root of your

These requirements are further detailed below, but if you simply copy the `HumanEval` folder, you will already be off to a great start.

## Implementing and Running Benchmark Tasks
The core of any benchmark are the tasks! To tasks that are runnable by AutoGenBench, you must adhere to AutoGenBench's templating and scenario expansion algorithms. These, together with an overview of execution, are provided below:

### Task Definitions

All tasks are stored in JSONL files (in subdirectories under `./Tasks`). Each line of a tasks file is a JSON object. The schema varies slightly based on if "template" specifies a _file_ or a _directory_.

If `template` points to a _file_, the format is:
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


If `template` points to a _directory_, the format is:

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


The `template` field can also take on a list value, but this usage is considered advanced and is not described here. See the code, or the `GAIA` benchmark for additional information about this option.


## Task Instance Expansion Algorithm

Once the tasks have been defined, as per above, they must be "instantiated" before they can be run. This instantiation happens automatically when the user issues the `autogenbench run` command, and involves creating a local folder to share with Docker. Each instance and repetition gets its own folder along the path: `./results/[scenario]/[instance_id]/[repetition]`. For the sake of brevity we will refer to this folder as the `DEST_FOLDER`.

The algorithm for populating the `DEST_FOLDER` is as follows:

1. Pre-populate DEST_FOLDER with all the basic starter files for running a scenario (found in `autogenbench/template`).
2. Recursively copy the template folder (if `template` in the json scenario definition points to a folder) to DEST_FOLDER. If the `template` instead points to a file, copy the file, but rename it to `scenario.py`
3. Apply any string replacement, as outlined in the prior section.
4. Write a run.sh file to DEST_FOLDER that will be executed by Docker when it is loaded. The `run.sh` is described below.

## Scenario Execution Algorithm

Once the task has been instantiated it is run (via run.sh). This script will execute the following steps:

1. If a file named `global_init.sh` is present, run it.
2. If a file named `scenario_init.sh` is present, run it.
3. Install the requirements.txt file (if running in Docker)
4. Run the Autogen scenario via `python scenario.py`
5. Clean up (delete cache, etc.)
6. If a file named `scenario_finalize.sh` is present, run it.
7. If a file named `global_finalize.sh` is present, run it.
8. echo "SCENARIO COMPLETE !#!#", signaling that all steps completed.

Notably, this means that scenarios can add custom init and teardown logic by including `scenario_init.sh` and `scenario_finalize.sh` files.

At the time of this writing, the run.sh file is as follows:

```sh
export AUTOGEN_TESTBED_SETTING="Docker"
umask 000

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
pip install -r requirements.txt
python scenario.py

# Clean up
if [ -d .cache ] ; then
    rm -Rf .cache
fi

# Run the scenario finalize script if it exists
if [ -f scenario_finalize.sh ] ; then
    . ./scenario_finalize.sh
fi

# Run the global finalize script if it exists
if [ -f global_finalize.sh ] ; then
    . ./global_finalize.sh
fi

echo SCENARIO COMPLETE !#!#
```

Be warned that this listing is provided here for illustration purposes, and may vary over time. The source of truth is the `run.sh` files found in the ``./results/[taskset]/[task_id]/[instance]`` folder.


## Integrating with the `tabulate` and `clone` commands.

The above details are sufficient to defining and running tasks, but if you wish to support the `autogenbench tabulate` and `autogenbench clone` command, a few additional steps are required.

### Tabulations

If you wish to leverage the default tabulation logic, it is as simple as arranging your scenarios to output the string "ALL TESTS PASSED !#!#" to the console in the event that a task was solved correctly.

If you wish to implement your own tabulation logic, simply create a file `Scripts/custom_tabulate.py` and include a `main(args)` method. Here, the `args` parameter will be provided by AutoGenBench, and is a drop-in replacement for `sys.argv`. In particular, `args[0]` will be the invocation command (similar to the executable or script name in `sys.argv`), and the remaining values `args[1:]` are the command line parameters.

Should you provide a custom tabulation script, please implement `--help` and `-h` options for documenting your interface.

The benchmark `scenarios/GAIA/Scripts/custom_tabulate.py` is a great example of custom tabulation. It also shows how you can re-use some components of the default tabulator to speed up development.


### Cloning

If you wish your benchmark to be available via the `autogenbench clone` command, you will need to take 3 additional steps:

#### Manifest
First, provide a `MANIFEST.json` file in the root of your benchmark. An example is provided below, from which you can see the schema:

```json
{
    "files": {
        "Templates/TwoAgents/prompt.txt": "samples/tools/testbed/scenarios/HumanEval/Templates/TwoAgents/prompt.txt",
        "Templates/TwoAgents/coding/my_tests.py": "samples/tools/testbed/scenarios/HumanEval/Templates/TwoAgents/coding/my_tests.py",
        "Templates/TwoAgents/scenario.py": "samples/tools/testbed/scenarios/HumanEval/Templates/TwoAgents/scenario.py",
        "README.md": "samples/tools/testbed/scenarios/HumanEval/README.md",
	"Scripts/init_tasks.py": "samples/tools/testbed/scenarios/HumanEval/Scripts/init_tasks.py",
	"Scripts/custom_tabulate.py": "samples/tools/testbed/scenarios/HumanEval/Scripts/custom_tabulate.py"
    }
}
```

The keys of the `files` dictionary are local paths, relative to your benchamrk's root directory. The values are relative paths in the AutoGen GitHub repository (relative to `https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/`), where {BRANCH} is defined in `autogenbench/clone_cmd.py`.

#### SCENARIOS dictionary
Second, you must add an entry to the `SCENARIOS` dictionary in `autogenbranch/clone_cmd.py`.

#### Scripts/init_tasks.py
Finally, you should provide an `Scripts/init_tasks.py` file, in your benchmark folder, and include a `main()` method therein. This method will be loaded and called automatically by `autogenbench clone`, after all manifest files have been downloaded. This `init_tasks.py` script is a great place to download benchmarks from their original sources, and then convert them to the JSONL format required by AutoGenBench:
- See `HumanEval/Scripts/init_tasks.py` for an example of how to expand a benchmark from an original GitHub repository.
- See `GAIA/Scripts/init_tasks.py` for an example of how to expand a benchmark from `Hugging Face Hub`.
- See `MATH/SCripts/init_tasks.py` for an example of how to expand a benchmark from an author-hosted website.
