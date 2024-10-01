#!/usr/bin/env python3 -m pytest

import json
import os
import sys
from functools import partial

import datasets
import numpy as np
import pytest

import autogen
from autogen.code_utils import (
    eval_function_completions,
    generate_assertions,
    generate_code,
    implement,
)
from autogen.math_utils import eval_math_responses, solve_problem
from test.oai.test_utils import KEY_LOC, OAI_CONFIG_LIST

here = os.path.abspath(os.path.dirname(__file__))


def yes_or_no_filter(context, response, **_):
    return context.get("yes_or_no_choice", False) is False or any(
        text in ["Yes.", "No."] for text in autogen.Completion.extract_text(response)
    )


def valid_json_filter(response, **_):
    for text in autogen.Completion.extract_text(response):
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
    config_list = autogen.config_list_from_models(
        KEY_LOC, exclude="aoai", model_list=["text-ada-001", "gpt-3.5-turbo", "text-davinci-003"]
    )
    response = autogen.Completion.create(
        context={"yes_or_no_choice": True},
        config_list=config_list,
        prompt="Is 37 a prime number? Please answer 'Yes.' or 'No.'",
        filter_func=yes_or_no_filter,
    )
    assert (
        autogen.Completion.extract_text(response)[0] in ["Yes.", "No."]
        or not response["pass_filter"]
        and response["config_id"] == 2
    )
    response = autogen.Completion.create(
        context={"yes_or_no_choice": False},
        config_list=config_list,
        prompt="Is 37 a prime number?",
        filter_func=yes_or_no_filter,
    )
    assert response["model"] == "text-ada-001"
    response = autogen.Completion.create(
        config_list=config_list,
        prompt="How to construct a json request to Bing API to search for 'latest AI news'? Return the JSON request.",
        filter_func=valid_json_filter,
    )
    assert response["config_id"] == 2 or response["pass_filter"], "the response must pass filter unless all fail"
    assert not response["pass_filter"] or json.loads(autogen.Completion.extract_text(response)[0])


def test_chatcompletion():
    params = autogen.ChatCompletion._construct_params(
        context=None,
        config={"model": "unknown"},
        prompt="hi",
    )
    assert "messages" in params
    params = autogen.Completion._construct_params(
        context=None,
        config={"model": "unknown"},
        prompt="hi",
    )
    assert "messages" not in params
    params = autogen.Completion._construct_params(
        context=None,
        config={"model": "gpt-4"},
        prompt="hi",
    )
    assert "messages" in params
    params = autogen.Completion._construct_params(
        context={"name": "there"},
        config={"model": "unknown"},
        prompt="hi {name}",
        allow_format_str_template=True,
    )
    assert params["prompt"] == "hi there"
    params = autogen.Completion._construct_params(
        context={"name": "there"},
        config={"model": "unknown"},
        prompt="hi {name}",
    )
    assert params["prompt"] != "hi there"


def test_multi_model():
    try:
        import openai
    except ImportError as exc:
        print(exc)
        return
    response = autogen.Completion.create(
        config_list=autogen.config_list_gpt4_gpt35(KEY_LOC),
        prompt="Hi",
    )
    print(response)


def test_nocontext():
    try:
        import diskcache
        import openai
    except ImportError as exc:
        print(exc)
        return
    response = autogen.Completion.create(
        model="text-ada-001",
        prompt="1+1=",
        max_tokens=1,
        use_cache=False,
        request_timeout=10,
        config_list=autogen.config_list_openai_aoai(KEY_LOC, exclude="aoai"),
    )
    print(response)
    code, _ = generate_code(
        config_list=autogen.config_list_from_json(
            OAI_CONFIG_LIST,
            file_location=KEY_LOC,
            filter_dict={
                "model": {
                    "gpt-4o-mini",
                    "gpt-3.5-turbo",
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

    solution, cost = solve_problem("1+1=", config_list=autogen.config_list_gpt4_gpt35(KEY_LOC))
    print(solution, cost)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="do not run on windows",
)
def test_humaneval(num_samples=1):
    gpt35_config_list = autogen.config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        filter_dict={
            "model": {
                "gpt-4o-mini",
                "gpt-3.5-turbo",
            },
        },
        file_location=KEY_LOC,
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
    autogen.Completion.clear_cache(cache_path_root="{here}/cache")
    autogen.Completion.set_cache(seed)
    try:
        import diskcache
        import openai
    except ImportError as exc:
        print(exc)
        return
    autogen.Completion.clear_cache(400)
    # no error should be raised
    response = autogen.Completion.create(
        context=test_data[0],
        config_list=autogen.config_list_from_models(KEY_LOC, model_list=["gpt-3.5-turbo"]),
        prompt="",
        max_tokens=1,
        max_retry_period=0,
        raise_on_ratelimit_or_timeout=False,
    )
    # assert response == -1
    config_list = autogen.config_list_openai_aoai(KEY_LOC)
    # a minimal tuning example
    config, _ = autogen.Completion.tune(
        data=tune_data,
        metric="success",
        mode="max",
        eval_func=eval_function_completions,
        n=1,
        prompt="{definition}",
        allow_format_str_template=True,
        config_list=config_list,
    )
    response = autogen.Completion.create(context=test_data[0], config_list=config_list, **config)
    # a minimal tuning example for tuning chat completion models using the Completion class
    config, _ = autogen.Completion.tune(
        data=tune_data,
        metric="succeed_assertions",
        mode="max",
        eval_func=eval_with_generated_assertions,
        n=1,
        model="text-davinci-003",
        prompt="{definition}",
        allow_format_str_template=True,
        config_list=config_list,
    )
    response = autogen.Completion.create(context=test_data[0], config_list=config_list, **config)
    # a minimal tuning example for tuning chat completion models using the ChatCompletion class
    config_list = autogen.config_list_openai_aoai(KEY_LOC)
    config, _ = autogen.ChatCompletion.tune(
        data=tune_data,
        metric="expected_success",
        mode="max",
        eval_func=eval_function_completions,
        n=1,
        messages=[{"role": "user", "content": "{definition}"}],
        config_list=config_list,
        allow_format_str_template=True,
        request_timeout=120,
    )
    response = autogen.ChatCompletion.create(context=test_data[0], config_list=config_list, **config)
    print(response)
    from openai import RateLimitError

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
    config2, analysis = autogen.Completion.tune(
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
        allow_format_str_template=True,
    )
    print(config2)
    print(analysis.best_result)
    print(test_data[0])
    response = autogen.Completion.create(context=test_data[0], config_list=config_list, **config2)
    print(response)
    autogen.Completion.data = test_data[:num_samples]
    result = autogen.Completion._eval(analysis.best_config, prune=False, eval_only=True)
    print("result without pruning", result)
    result = autogen.Completion.test(test_data[:num_samples], config_list=config_list, **config2)
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
        import diskcache
        import openai
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

    autogen.Completion.set_cache(seed)
    config_list = autogen.config_list_openai_aoai(KEY_LOC)
    vanilla_config = {
        "model": "text-ada-001",
        "temperature": 1,
        "max_tokens": 1024,
        "n": 1,
        "prompt": prompts[0],
        "stop": "###",
    }
    test_data_sample = test_data[0:3]
    result = autogen.Completion.test(test_data_sample, eval_math_responses, config_list=config_list, **vanilla_config)
    result = autogen.Completion.test(
        test_data_sample,
        eval_math_responses,
        agg_method="median",
        config_list=config_list,
        **vanilla_config,
    )

    def my_median(results):
        return np.median(results)

    def my_average(results):
        return np.mean(results)

    result = autogen.Completion.test(
        test_data_sample,
        eval_math_responses,
        agg_method=my_median,
        **vanilla_config,
    )
    result = autogen.Completion.test(
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

    config, _ = autogen.Completion.tune(
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
        config_list=config_list,
    )
    print("tuned config", config)
    result = autogen.Completion.test(test_data_sample, config_list=config_list, **config)
    print("result from tuned config:", result)
    print("empty responses", eval_math_responses([], None))


if __name__ == "__main__":
    import openai

    config_list = autogen.config_list_openai_aoai(KEY_LOC)
    assert len(config_list) >= 3, config_list
    openai.api_key = os.environ["OPENAI_API_KEY"]

    # test_filter()
    # test_chatcompletion()
    # test_multi_model()
    # test_nocontext()
    # test_humaneval(1)
    test_math(1)
