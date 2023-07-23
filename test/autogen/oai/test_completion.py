import datasets
import sys
import numpy as np
import pytest
from functools import partial
import os
import json
from flaml import oai
from flaml.autogen.code_utils import (
    eval_function_completions,
    generate_assertions,
    implement,
    generate_code,
    improve_function,
    improve_code,
)
from flaml.autogen.math_utils import eval_math_responses, solve_problem

KEY_LOC = "test/autogen"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"
here = os.path.abspath(os.path.dirname(__file__))


def yes_or_no_filter(context, response, **_):
    return context.get("yes_or_no_choice", False) is False or any(
        text in ["Yes.", "No."] for text in oai.Completion.extract_text(response)
    )


def valid_json_filter(response, **_):
    for text in oai.Completion.extract_text(response):
        try:
            json.loads(text)
            return True
        except ValueError:
            pass
    return False


def test_filter():
    try:
        import openai
    except ImportError as exc:
        print(exc)
        return
    response = oai.Completion.create(
        context={"yes_or_no_choice": True},
        config_list=[{"model": "text-ada-001"}, {"model": "gpt-3.5-turbo"}, {"model": "text-davinci-003"}],
        prompt="Is 37 a prime number? Please answer 'Yes.' or 'No.'",
        filter_func=yes_or_no_filter,
    )
    assert (
        oai.Completion.extract_text(response)[0] in ["Yes.", "No."]
        or not response["pass_filter"]
        and response["config_id"] == 2
    )
    response = oai.Completion.create(
        context={"yes_or_no_choice": False},
        config_list=[{"model": "text-ada-001"}, {"model": "gpt-3.5-turbo"}, {"model": "text-davinci-003"}],
        prompt="Is 37 a prime number?",
        filter_func=yes_or_no_filter,
    )
    assert response["model"] == "text-ada-001"
    response = oai.Completion.create(
        config_list=[{"model": "text-ada-001"}, {"model": "gpt-3.5-turbo"}, {"model": "text-davinci-003"}],
        prompt="How to construct a json request to Bing API to search for 'latest AI news'? Return the JSON request.",
        filter_func=valid_json_filter,
    )
    assert response["config_id"] == 2 or response["pass_filter"], "the response must pass filter unless all fail"
    assert not response["pass_filter"] or json.loads(oai.Completion.extract_text(response)[0])


def test_chatcompletion():
    params = oai.ChatCompletion._construct_params(
        data_instance=None,
        config={"model": "unknown"},
        prompt="hi",
    )
    assert "messages" in params
    params = oai.Completion._construct_params(
        data_instance=None,
        config={"model": "unknown"},
        prompt="hi",
    )
    assert "messages" not in params
    params = oai.Completion._construct_params(
        data_instance=None,
        config={"model": "gpt-4"},
        prompt="hi",
    )
    assert "messages" in params


def test_multi_model():
    try:
        import openai
    except ImportError as exc:
        print(exc)
        return
    response = oai.Completion.create(
        config_list=oai.config_list_gpt4_gpt35(KEY_LOC),
        prompt="Hi",
    )
    print(response)


def test_improve():
    try:
        import openai
        import diskcache
    except ImportError as exc:
        print(exc)
        return
    config_list = oai.config_list_openai_aoai(KEY_LOC)
    improved, _ = improve_function(
        "flaml/autogen/math_utils.py",
        "solve_problem",
        "Solve math problems accurately, by avoiding calculation errors and reduce reasoning errors.",
        config_list=config_list,
    )
    with open(f"{here}/math_utils.py.improved", "w") as f:
        f.write(improved)
    suggestion, _ = improve_code(
        ["flaml/autogen/code_utils.py", "flaml/autogen/math_utils.py"],
        "leverage generative AI smartly and cost-effectively",
        config_list=config_list,
    )
    print(suggestion)
    improvement, cost = improve_code(
        ["flaml/autogen/code_utils.py", "flaml/autogen/math_utils.py"],
        "leverage generative AI smartly and cost-effectively",
        suggest_only=False,
        config_list=config_list,
    )
    print(cost)
    with open(f"{here}/suggested_improvement.txt", "w") as f:
        f.write(improvement)


def test_nocontext():
    try:
        import openai
        import diskcache
    except ImportError as exc:
        print(exc)
        return
    response = oai.Completion.create(
        model="text-ada-001", prompt="1+1=", max_tokens=1, use_cache=False, request_timeout=10
    )
    print(response)
    code, _ = generate_code(
        config_list=oai.config_list_from_json(
            OAI_CONFIG_LIST,
            file_location=KEY_LOC,
            filter_dict={
                "model": {
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k",
                    "gpt-3.5-turbo-0301",
                    "chatgpt-35-turbo-0301",
                    "gpt-35-turbo-v0301",
                },
            },
        ),
        messages=[
            {
                "role": "system",
                "content": "You want to become a better assistant by learning new skills and improving your existing ones.",
            },
            {
                "role": "user",
                "content": "Write reusable code to use web scraping to get information from websites.",
            },
        ],
    )
    print(code)

    solution, cost = solve_problem("1+1=", config_list=oai.config_list_gpt4_gpt35(KEY_LOC))
    print(solution, cost)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="do not run on windows",
)
def test_humaneval(num_samples=1):
    gpt35_config_list = oai.config_list_from_json(
        env_or_file="OAI_CONFIG_LIST",
        filter_dict={
            "model": {
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-0301",
                "chatgpt-35-turbo-0301",
                "gpt-35-turbo-v0301",
            },
        },
    )
    assertions = partial(generate_assertions, config_list=gpt35_config_list)
    eval_with_generated_assertions = partial(
        eval_function_completions,
        assertions=assertions,
    )

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
    oai.Completion.clear_cache(cache_path_root="{here}/cache")
    oai.Completion.set_cache(seed)
    try:
        import openai
        import diskcache
    except ImportError as exc:
        print(exc)
        return
    oai.Completion.clear_cache(400)
    # no error should be raised
    response = oai.Completion.create(
        context=test_data[0],
        config_list=[{"model": "gpt-3.5-turbo"}],
        prompt="",
        max_tokens=1,
        retry_timeout=0,
        raise_on_ratelimit_or_timeout=False,
    )
    # assert response == -1
    # a minimal tuning example
    config, _ = oai.Completion.tune(
        data=tune_data,
        metric="success",
        mode="max",
        eval_func=eval_function_completions,
        n=1,
        prompt="{definition}",
    )
    response = oai.Completion.create(context=test_data[0], **config)
    # a minimal tuning example for tuning chat completion models using the Completion class
    config, _ = oai.Completion.tune(
        data=tune_data,
        metric="succeed_assertions",
        mode="max",
        eval_func=eval_with_generated_assertions,
        n=1,
        model="text-davinci-003",
        prompt="{definition}",
    )
    response = oai.Completion.create(context=test_data[0], **config)
    # a minimal tuning example for tuning chat completion models using the ChatCompletion class
    config_list = oai.config_list_openai_aoai(KEY_LOC)
    config, _ = oai.ChatCompletion.tune(
        data=tune_data,
        metric="expected_success",
        mode="max",
        eval_func=eval_function_completions,
        n=1,
        messages=[{"role": "user", "content": "{definition}"}],
        config_list=config_list,
    )
    response = oai.ChatCompletion.create(context=test_data[0], config_list=config_list, **config)
    print(response)
    from openai.error import RateLimitError

    try:
        code, cost, selected = implement(tune_data[1], [{**config_list[-1], **config}])
    except RateLimitError:
        code, cost, selected = implement(
            tune_data[1],
            [{**config_list[0], "model": "text-ada-001", "prompt": config["messages"]["content"]}],
            assertions=assertions,
        )
    print(code)
    print(cost)
    assert selected == 0
    print(eval_function_completions([code], **tune_data[1]))
    # a more comprehensive tuning example
    config2, analysis = oai.Completion.tune(
        data=tune_data,
        metric="success",
        mode="max",
        eval_func=eval_with_generated_assertions,
        log_file_name="logs/humaneval.log",
        inference_budget=0.002,
        optimization_budget=2,
        num_samples=num_samples,
        # logging_level=logging.INFO,
        prompt=[
            "{definition}",
            "# Python 3{definition}",
            "Complete the following Python function:{definition}",
        ],
        stop=[["\nclass", "\ndef", "\nif", "\nprint"], None],  # the stop sequences
        config_list=config_list,
    )
    print(config2)
    print(analysis.best_result)
    print(test_data[0])
    response = oai.Completion.create(context=test_data[0], **config2)
    print(response)
    oai.Completion.data = test_data[:num_samples]
    result = oai.Completion._eval(analysis.best_config, prune=False, eval_only=True)
    print("result without pruning", result)
    result = oai.Completion.test(test_data[:num_samples], **config2)
    print(result)
    try:
        code, cost, selected = implement(
            tune_data[1], [{**config_list[-2], **config2}, {**config_list[-1], **config}], assertions=assertions
        )
    except RateLimitError:
        code, cost, selected = implement(
            tune_data[1],
            [
                {**config_list[-3], **config2},
                {**config_list[0], "model": "text-ada-001", "prompt": config["messages"]["content"]},
            ],
            assertions=assertions,
        )
    print(code)
    print(cost)
    print(selected)
    print(eval_function_completions([code], **tune_data[1]))


def test_math(num_samples=-1):
    try:
        import openai
        import diskcache
    except ImportError as exc:
        print(exc)
        return

    seed = 41
    data = datasets.load_dataset("competition_math")
    train_data = data["train"].shuffle(seed=seed)
    test_data = data["test"].shuffle(seed=seed)
    n_tune_data = 20
    tune_data = [
        {
            "problem": train_data[x]["problem"],
            "solution": train_data[x]["solution"],
        }
        for x in range(len(train_data))
        if train_data[x]["level"] == "Level 1"
    ][:n_tune_data]
    test_data = [
        {
            "problem": test_data[x]["problem"],
            "solution": test_data[x]["solution"],
        }
        for x in range(len(test_data))
        if test_data[x]["level"] == "Level 1"
    ]
    print(
        "max tokens in tuning data's canonical solutions",
        max([len(x["solution"].split()) for x in tune_data]),
    )
    print(len(tune_data), len(test_data))
    # prompt template
    prompts = [
        lambda data: "%s Solve the problem carefully. Simplify your answer as much as possible. Put the final answer in \\boxed{}."
        % data["problem"]
    ]

    oai.Completion.set_cache(seed)
    vanilla_config = {
        "model": "text-davinci-003",
        "temperature": 1,
        "max_tokens": 2048,
        "n": 1,
        "prompt": prompts[0],
        "stop": "###",
    }
    test_data_sample = test_data[0:3]
    result = oai.Completion.test(test_data_sample, eval_math_responses, **vanilla_config)
    result = oai.Completion.test(
        test_data_sample,
        eval_math_responses,
        agg_method="median",
        **vanilla_config,
    )

    def my_median(results):
        return np.median(results)

    def my_average(results):
        return np.mean(results)

    result = oai.Completion.test(
        test_data_sample,
        eval_math_responses,
        agg_method=my_median,
        **vanilla_config,
    )
    result = oai.Completion.test(
        test_data_sample,
        eval_math_responses,
        agg_method={
            "expected_success": my_median,
            "success": my_average,
            "success_vote": my_average,
            "votes": np.mean,
        },
        **vanilla_config,
    )

    print(result)

    config, _ = oai.Completion.tune(
        data=tune_data,  # the data for tuning
        metric="expected_success",  # the metric to optimize
        mode="max",  # the optimization mode
        eval_func=eval_math_responses,  # the evaluation function to return the success metrics
        # log_file_name="logs/math.log",  # the log file name
        inference_budget=0.002,  # the inference budget (dollar)
        optimization_budget=0.01,  # the optimization budget (dollar)
        num_samples=num_samples,
        prompt=prompts,  # the prompt templates to choose from
        stop="###",  # the stop sequence
    )
    print("tuned config", config)
    result = oai.Completion.test(test_data_sample, config_list=oai.config_list_openai_aoai(KEY_LOC), **config)
    print("result from tuned config:", result)
    print("empty responses", eval_math_responses([], None))


if __name__ == "__main__":
    import openai

    config_list = oai.config_list_openai_aoai(KEY_LOC)
    assert len(config_list) >= 3, config_list
    openai.api_key = os.environ["OPENAI_API_KEY"]

    # test_filter()
    # test_chatcompletion()
    # test_multi_model()
    # test_improve()
    # test_nocontext()
    test_humaneval(1)
    # test_math(1)
