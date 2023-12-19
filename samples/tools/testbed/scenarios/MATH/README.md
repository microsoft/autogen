## Get json file to run

This will convert the math problems to json format and put it in the `scenarios/MATH` folder.
```sh
cd samples/tools/testbed/
python scenarios/MATH/problems_to_json.py
```

## Run the testbed

Note: this will first run autogen on the math problems, and then use a LLM as answer checker to check the answers.
This means the results is not 100% accurate.

```sh
python run_scenarios.py scenarios/MATH/problems.jsonl -c <config_list> --requirements math_requirements.txt
```

## Get the correct count
Use `--path` or `-p` to specify the path to the problem directory, the default is `./results/problems/`, which is the default save path of this testbed.
```sh
python scenarios/MATH/count_correct_math.py --path <path_to_problem_dir>
```

Example output:
```
Trial 0 | Total Correct: 10 | Total Problems: 17
```
