# AutoGen - OpenAI

FLAML offers a cost-effective hyperparameter optimization technique [EcoOptiGen](https://arxiv.org/abs/2303.04673) for tuning Large Language Models. Our study finds that tuning hyperparameters can significantly improve the utility of them.
In this example, we will tune several hyperparameters for the OpenAI's completion API, including the temperature, prompt and n (number of completions), to optimize the inference performance for a code generation task.

### Prerequisites

Install the [openai] option. The OpenAI integration is in preview.
```bash
pip install "flaml[openai]==1.2.0"
```

Setup your OpenAI key:
```python
import os

if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "<your OpenAI API key here>"
```

If you use Azure OpenAI, set up Azure using the following code:

```python
import openai

openai.api_type = "azure"
openai.api_base = "https://<your_endpoint>.openai.azure.com/"
openai.api_version = "2023-03-15-preview"  # change if necessary
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
        "definition": data[x]["prompt"],
        "test": data[x]["test"],
        "entry_point": data[x]["entry_point"],
    }
    for x in range(n_tune_data)
]
test_data = [
    {
        "definition": data[x]["prompt"],
        "test": data[x]["test"],
        "entry_point": data[x]["entry_point"],
    }
    for x in range(n_tune_data, len(data))
]
```

### Define the metric

Before starting tuning, you need to define the metric for the optimization. For each code generation task, we can use the model to generate multiple candidate responses, and then select one from them. If the final selected response can pass a unit test, we consider the task as successfully solved. Then we can define the average success rate on a collection of tasks as the optimization metric.

```python
from functools import partial
from flaml.autogen.code_utils import eval_function_completions, generate_assertions

eval_with_generated_assertions = partial(eval_function_completions, assertions=generate_assertions)
```

This function will first generate assertion statements for each problem. Then, it uses the assertions to select the generated responses.

### Tune the hyperparameters

The tuning will be performed under the specified optimization budgets.

* inference_budget is the target average inference budget per instance in the benchmark. For example, 0.02 means the target inference budget is 0.02 dollars, which translates to 1000 tokens (input + output combined) if the text Davinci model is used.
* optimization_budget is the total budget allowed to perform the tuning. For example, 5 means 5 dollars are allowed in total, which translates to 250K tokens for the text Davinci model.
* num_sumples is the number of different hyperparameter configurations which is allowed to try. The tuning will stop after either num_samples trials or after optimization_budget dollars spent, whichever happens first. -1 means no hard restriction in the number of trials and the actual number is decided by optimization_budget.

Users can specify tuning data, optimization metric, optimization mode, evaluation function, search spaces etc.

```python
from flaml import oai

config, analysis = oai.Completion.tune(
    data=tune_data,  # the data for tuning
    metric="success",  # the metric to optimize
    mode="max",  # the optimization mode
    eval_func=eval_with_generated_assertions,  # the evaluation function to return the success metrics
    # log_file_name="logs/humaneval.log",  # the log file name
    inference_budget=0.05,  # the inference budget (dollar per instance)
    optimization_budget=3,  # the optimization budget (dollar in total)
    # num_samples can further limit the number of trials for different hyperparameter configurations;
    # -1 means decided by the optimization budget only
    num_samples=-1,
    prompt=[
        "{definition}",
        "# Python 3{definition}",
        "Complete the following Python function:{definition}",
    ],  # the prompt templates to choose from
    stop=[["\nclass", "\ndef", "\nif", "\nprint"], None],  # the stop sequences
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
print(eval_with_generated_assertions(oai.Completion.extract_text(response), **tune_data[1]))
```

#### Evaluate the success rate on the test data

You can use flaml's `oai.Completion.test` to evaluate the performance of an entire dataset with the tuned config.

```python
result = oai.Completion.test(test_data, config)
print("performance on test data with the tuned config:", result)
```

The result will vary with the inference budget and optimization budget.

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/autogen_openai.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/autogen_openai.ipynb)
