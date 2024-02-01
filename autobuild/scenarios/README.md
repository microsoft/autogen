## Instruction

We use `autogenbench` to test all scenarios in our benchmark. For the detailed instruction of `autogenbench`, please refer to [autogenbench](https://microsoft.github.io/autogen/blog/2024/01/25/AutoGenBench/).
We also provided some brief instructions for `autogenbench` below.

## Installation

`autogenbench` requires the latest version of `pyautogen`. You can install `pyautogen`. You can install them by running the following command:
```bash
pip install pyautogen autogenbench
```

## Usage

Use following command to run the benchmark for each scenario:
```bash
cd [SCENARIO FOLDER. For example, /path/to/scenarious/MATH]
python Scripts/init_tasks.py  // initialize the tasks
autogenbench run Tasks/[TASK YOU WANT TO RUN].jsonl  // run the task
autogenbench tabulate results/[TASK YOU WANT TO RUN]  // print the results in tabulate.
```

if you want to debug, set `-s 1` to use a single data for testing:
```bash
autogenbench run Tasks/[TASK YOU WANT TO RUN].jsonl -s 1
```

## Contribute

To contribute to the benchmark, you need to prepare the following files:
- `Scripts/init_tasks.py`: This file is used to initialize the tasks for the benchmark, including dataset and prompt loading, and task json generation. You can define the substitution of the placeholder like `__PROMPT__` inside the Templates in the `init_tasks.py`.
- `Templates/[YOUR_TASK]/scenario.py`: The process of your method as a scenario.
- `Templates/[YOUR_TASK]/[EXTRA_FILES]`: The extra files needed for your method. For example, to record the results. 
- `MANIFEST.json`: including all files in this scenario.
- `README.md`: Should include the reference of the dataset and provide some brief instruction of how to run.
