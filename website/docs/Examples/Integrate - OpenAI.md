FLAML has integrated the OpenAI's completion API. In this example, we will tune several hyperparameters including the temperature, prompt and n to optimize the inference performance of OpenAI's completion API for a code generation task. Our study shows that tuning hyperparameters can significantly affect the utility of the OpenAI API.

### Prerequisites

Install the [openai] option. The option is available in flaml since version 1.1.3. This feature is subject to change in future versions.
```bash
pip install "flaml[openai]==1.1.3"
```


Setup your OpenAI key:
```python
import os

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "<your OpenAI API key here>"
```

If you use Azure OpenAI, set up Azure using the following code:

```python
openai.api_type = "azure"
openai.api_base = "https://<your_endpoint>.openai.azure.com/"
openai.api_version = "2022-12-01"  # change if necessary
```

### Load the dataset

We use the HumanEval dataset as an example. The dataset contains 164 examples. We use the first 20 for tuning the generation hyperparameters and the remaining for evaluation. In each example, the "prompt" is the prompt string for eliciting the code generation, "test" is the Python code for unit test for the example, and "entry_point" is the function name to be tested.

```python
import datasets

seed = 41
data = datasets.load_dataset("openai_humaneval")["test"].shuffle(seed=seed)
n_tune_data = 20
tune_data = [
    {
        "prompt": data[x]["prompt"],
        "test": data[x]["test"],
        "entry_point": data[x]["entry_point"],
    }
    for x in range(n_tune_data)
]
test_data = [
    {
        "prompt": data[x]["prompt"],
        "test": data[x]["test"],
        "entry_point": data[x]["entry_point"],
    }
    for x in range(n_tune_data, len(data))
]
```

### Defining the metric

Before starting tuning, you need to define the metric for the optimization. For the HumanEval dataset, we use the success rate as the metric. So if one of the returned responses can pass the test, we consider the task as successfully solved. Then we can define the mean success rate of a collection of tasks.

#### Define a code executor

First, we write a simple code executor. The code executor takes the generated code and the test code as the input, and execute them with a timer.

```python
import signal
import subprocess
import sys

def timeout_handler(signum, frame):
    raise TimeoutError("Timed out!")

signal.signal(signal.SIGALRM, timeout_handler)
max_exec_time = 3  # seconds

def execute_code(code):
    code = code.strip()
    with open("codetest.py", "w") as fout:
        fout.write(code)
    try:
        signal.alarm(max_exec_time)
        result = subprocess.run(
            [sys.executable, "codetest.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        signal.alarm(0)
    except TimeoutError:
        return 0
    return int(result.returncode == 0)
```

This function will create a temp file "codetest.py" and execute it in a separate process. It allows for 3 seconds to finish that code.

#### Define a function to evaluate the success for a given program synthesis task

Now we define the success metric.

```python
def success_metrics(responses, prompt, test, entry_point):
    """Check if the task is successful.

    Args:
        responses (list): The list of responses.
        prompt (str): The input prompt.
        test (str): The test code.
        entry_point (str): The name of the function.

    Returns:
        dict: The success metrics.
    """
    success_list = []
    n = len(responses)
    for i in range(n):
        response = responses[i]
        code = f"{prompt}{response}\n{test}\ncheck({entry_point})"
        succeed = execute_code(code)
        success_list.append(succeed)
    return {
        "expected_success": 1 - pow(1 - sum(success_list) / n, n),
        "success": any(s for s in success_list),
    }
```

### Tuning Hyperparameters for OpenAI

The tuning will take a while to finish, depending on the optimization budget (~1 min for the current budget). The tuning will be performed under the specified optimization budgets.

* inference_budget is the target average inference budget per instance in the benchmark. For example, 0.02 means the target inference budget is 0.02 dollars, which translates to 1000 tokens (input + output combined) if the text Davinci model is used.
* optimization_budget is the total budget allowed to perform the tuning. For example, 5 means 5 dollars are allowed in total, which translates to 250K tokens for the text Davinci model.
* num_sumples is the number of different hyperparameter configurations which is allowed to try. The tuning will stop after either num_samples trials or after optimization_budget dollars spent, whichever happens first. -1 means no hard restriction in the number of trials and the actual number is decided by optimization_budget.

Users can specify tuning data, optimization metric, optimization mode, evaluation function, search spaces etc.

```python
config, analysis = oai.Completion.tune(
    data=tune_data,  # the data for tuning
    metric="expected_success",  # the metric to optimize
    mode="max",  # the optimization mode
    eval_func=success_metrics,  # the evaluation function to return the success metrics
    # log_file_name="logs/humaneval.log",  # the log file name
    inference_budget=0.1,  # the inference budget (dollar)
    optimization_budget=4,  # the optimization budget (dollar)
    # num_samples can further limit the number of trials for different hyperparameter configurations;
    # -1 means decided by the optimization budget only
    num_samples=-1,
    model=tune.choice(
        [
            # These two models are in Beta test and free to use from OpenAI as of Feb 2023,
            # so no actual cost will incur (please double check when you run it). They are not free in Azure OpenAI.
            # The optimization is based on the price in Azure OpenAI as of Feb 2023.
            "code-cushman-001",
            "code-davinci-002",
        ]
    ),
    prompt=[
        "{prompt}",
        "# Python 3{prompt}",
        "Complete the following Python function:{prompt}",
        "Complete the following Python function while including necessary import statements inside the function:{prompt}",
    ],  # the prompt templates to choose from
    stop=["\nclass", "\ndef", "\nif", "\nprint"],  # the stop sequence
)
```

#### Output tuning results

After the tuning, we can print out the optimized config and the result found by FLAML:

```python
print("optimized config", config)
print("best result on tuning data", analysis.best_result)
```

#### Make a request with the tuned config

We can apply the tuned config to the request for an instance:

```python
responses = oai.Completion.create(context=tune_data[1], **config)
print(responses)
print(success_metrics([response["text"].rstrip() for response in responses["choices"]], **tune_data[1]))
```

#### Evaluate the success rate on the test data

You can use flaml's oai.Completion.eval to evaluate the performance of an entire dataset with the tuned config. To do that you need to set oai.Completion.data to the data to evaluate. The following code will take a while to evaluate all the 144 test data instances. Compared to the baseline success rate (0.46) on the HELM benchmark, the tuned config has a success rate of 0.68. It can be further improved if the inference budget and optimization budget are further increased.

```python
oai.Completion.data = test_data
result = oai.Completion.eval(analysis.best_config, prune=False, eval_only=True)
print(result)
```

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/integrate_openai.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/integrate_openai.ipynb)
