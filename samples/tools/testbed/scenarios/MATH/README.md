## Get json file to run

```sh
cd samples/tools/testbed/
python scenarios/MATH/problems_to_json.py
```

## Run the testbed

```sh
python run_scenarios.py scenarios/MATH/problems.jsonl -c <config_list> --requirements math_requirements.txt
```

## Get the correct count

```sh
python scenarios/MATH/count_correct_math.py <path_to_problem_dir>```
