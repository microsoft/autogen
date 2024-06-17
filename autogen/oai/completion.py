import logging
import shutil
import sys
import time
from collections import defaultdict
from time import sleep
from typing import Callable, Dict, List, Optional, Union

import numpy as np
from flaml import BlendSearch, tune
from flaml.automl.logger import logger_formatter
from flaml.tune.space import is_constant

from .openai_utils import get_key

try:
    import diskcache
    import openai
    from openai import (
        APIConnectionError,
        APIError,
        AuthenticationError,
        BadRequestError,
        RateLimitError,
        Timeout,
    )
    from openai import Completion as openai_Completion

    ERROR = None
    assert openai.__version__ < "1"
except (AssertionError, ImportError):
    openai_Completion = object
    # The autogen.Completion class requires openai<1
    ERROR = AssertionError("(Deprecated) The autogen.Completion class requires openai<1 and diskcache. ")

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add the console handler.
    _ch = logging.StreamHandler(stream=sys.stdout)
    _ch.setFormatter(logger_formatter)
    logger.addHandler(_ch)


class Completion(openai_Completion):
    """(openai<1) A class for OpenAI completion API.

    It also supports: ChatCompletion, Azure OpenAI API.
    """

    # set of models that support chat completion
    chat_models = {
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0301",  # deprecate in Sep
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-16k-0613",
        "gpt-35-turbo",
        "gpt-35-turbo-16k",
        "gpt-4",
        "gpt-4-32k",
        "gpt-4-32k-0314",  # deprecate in Sep
        "gpt-4-0314",  # deprecate in Sep
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }

    # price per 1k tokens
    price1K = {
        "text-ada-001": 0.0004,
        "text-babbage-001": 0.0005,
        "text-curie-001": 0.002,
        "code-cushman-001": 0.024,
        "code-davinci-002": 0.1,
        "text-davinci-002": 0.02,
        "text-davinci-003": 0.02,
        "gpt-3.5-turbo": (0.0015, 0.002),
        "gpt-3.5-turbo-instruct": (0.0015, 0.002),
        "gpt-3.5-turbo-0301": (0.0015, 0.002),  # deprecate in Sep
        "gpt-3.5-turbo-0613": (0.0015, 0.002),
        "gpt-3.5-turbo-16k": (0.003, 0.004),
        "gpt-3.5-turbo-16k-0613": (0.003, 0.004),
        "gpt-35-turbo": (0.0015, 0.002),
        "gpt-35-turbo-16k": (0.003, 0.004),
        "gpt-35-turbo-instruct": (0.0015, 0.002),
        "gpt-4": (0.03, 0.06),
        "gpt-4-32k": (0.06, 0.12),
        "gpt-4-0314": (0.03, 0.06),  # deprecate in Sep
        "gpt-4-32k-0314": (0.06, 0.12),  # deprecate in Sep
        "gpt-4-0613": (0.03, 0.06),
        "gpt-4-32k-0613": (0.06, 0.12),
    }

    default_search_space = {
        "model": tune.choice(
            [
                "text-ada-001",
                "text-babbage-001",
                "text-davinci-003",
                "gpt-3.5-turbo",
                "gpt-4",
            ]
        ),
        "temperature_or_top_p": tune.choice(
            [
                {"temperature": tune.uniform(0, 2)},
                {"top_p": tune.uniform(0, 1)},
            ]
        ),
        "max_tokens": tune.lograndint(50, 1000),
        "n": tune.randint(1, 100),
        "prompt": "{prompt}",
    }

    cache_seed = 41
    cache_path = f".cache/{cache_seed}"
    # retry after this many seconds
    retry_wait_time = 10
    # fail a request after hitting RateLimitError for this many seconds
    max_retry_period = 120
    # time out for request to openai server
    request_timeout = 60

    openai_completion_class = not ERROR and openai.Completion
    _total_cost = 0
    optimization_budget = None

    _history_dict = _count_create = None

    @classmethod
    def set_cache(cls, seed: Optional[int] = 41, cache_path_root: Optional[str] = ".cache"):
        """Set cache path.

        Args:
            seed (int, Optional): The integer identifier for the pseudo seed.
                Results corresponding to different seeds will be cached in different places.
            cache_path (str, Optional): The root path for the cache.
                The complete cache path will be {cache_path_root}/{seed}.
        """
        cls.cache_seed = seed
        cls.cache_path = f"{cache_path_root}/{seed}"

    @classmethod
    def clear_cache(cls, seed: Optional[int] = None, cache_path_root: Optional[str] = ".cache"):
        """Clear cache.

        Args:
            seed (int, Optional): The integer identifier for the pseudo seed.
                If omitted, all caches under cache_path_root will be cleared.
            cache_path (str, Optional): The root path for the cache.
                The complete cache path will be {cache_path_root}/{seed}.
        """
        if seed is None:
            shutil.rmtree(cache_path_root, ignore_errors=True)
            return
        with diskcache.Cache(f"{cache_path_root}/{seed}") as cache:
            cache.clear()

    @classmethod
    def _book_keeping(cls, config: Dict, response):
        """Book keeping for the created completions."""
        if response != -1 and "cost" not in response:
            response["cost"] = cls.cost(response)
        if cls._history_dict is None:
            return
        if cls._history_compact:
            value = {
                "created_at": [],
                "cost": [],
                "token_count": [],
            }
            if "messages" in config:
                messages = config["messages"]
                if len(messages) > 1 and messages[-1]["role"] != "assistant":
                    existing_key = get_key(messages[:-1])
                    value = cls._history_dict.pop(existing_key, value)
                key = get_key(messages + [choice["message"] for choice in response["choices"]])
            else:
                key = get_key([config["prompt"]] + [choice.get("text") for choice in response["choices"]])
            value["created_at"].append(cls._count_create)
            value["cost"].append(response["cost"])
            value["token_count"].append(
                {
                    "model": response["model"],
                    "prompt_tokens": response["usage"]["prompt_tokens"],
                    "completion_tokens": response["usage"].get("completion_tokens", 0),
                    "total_tokens": response["usage"]["total_tokens"],
                }
            )
            cls._history_dict[key] = value
            cls._count_create += 1
            return
        cls._history_dict[cls._count_create] = {
            "request": config,
            "response": response.to_dict_recursive(),
        }
        cls._count_create += 1

    @classmethod
    def _get_response(cls, config: Dict, raise_on_ratelimit_or_timeout=False, use_cache=True):
        """Get the response from the openai api call.

        Try cache first. If not found, call the openai api. If the api call fails, retry after retry_wait_time.
        """
        config = config.copy()
        key = get_key(config)
        if use_cache:
            response = cls._cache.get(key, None)
            if response is not None and (response != -1 or not raise_on_ratelimit_or_timeout):
                # print("using cached response")
                cls._book_keeping(config, response)
                return response
        openai_completion = (
            openai.ChatCompletion
            if config["model"].replace("gpt-35-turbo", "gpt-3.5-turbo") in cls.chat_models
            or issubclass(cls, ChatCompletion)
            else openai.Completion
        )
        start_time = time.time()
        request_timeout = cls.request_timeout
        max_retry_period = config.pop("max_retry_period", cls.max_retry_period)
        retry_wait_time = config.pop("retry_wait_time", cls.retry_wait_time)
        while True:
            try:
                if "request_timeout" in config:
                    response = openai_completion.create(**config)
                else:
                    response = openai_completion.create(request_timeout=request_timeout, **config)
            except APIConnectionError:
                # transient error
                logger.info(f"retrying in {retry_wait_time} seconds...", exc_info=1)
                sleep(retry_wait_time)
            except APIError as err:
                error_code = err and err.json_body and isinstance(err.json_body, dict) and err.json_body.get("error")
                if isinstance(error_code, dict):
                    error_code = error_code.get("code")
                if error_code == "content_filter":
                    raise
                # transient error
                logger.info(f"retrying in {retry_wait_time} seconds...", exc_info=1)
                sleep(retry_wait_time)
            except (RateLimitError, Timeout) as err:
                time_left = max_retry_period - (time.time() - start_time + retry_wait_time)
                if (
                    time_left > 0
                    and isinstance(err, RateLimitError)
                    or time_left > request_timeout
                    and isinstance(err, Timeout)
                    and "request_timeout" not in config
                ):
                    if isinstance(err, Timeout):
                        request_timeout <<= 1
                    request_timeout = min(request_timeout, time_left)
                    logger.info(f"retrying in {retry_wait_time} seconds...", exc_info=1)
                    sleep(retry_wait_time)
                elif raise_on_ratelimit_or_timeout:
                    raise
                else:
                    response = -1
                    if use_cache and isinstance(err, Timeout):
                        cls._cache.set(key, response)
                    logger.warning(
                        f"Failed to get response from openai api due to getting RateLimitError or Timeout for {max_retry_period} seconds."
                    )
                    return response
            except BadRequestError:
                if "azure" in config.get("api_type", openai.api_type) and "model" in config:
                    # azure api uses "engine" instead of "model"
                    config["engine"] = config.pop("model").replace("gpt-3.5-turbo", "gpt-35-turbo")
                else:
                    raise
            else:
                if use_cache:
                    cls._cache.set(key, response)
                cls._book_keeping(config, response)
                return response

    @classmethod
    def _get_max_valid_n(cls, key, max_tokens):
        # find the max value in max_valid_n_per_max_tokens
        # whose key is equal or larger than max_tokens
        return max(
            (value for k, value in cls._max_valid_n_per_max_tokens.get(key, {}).items() if k >= max_tokens),
            default=1,
        )

    @classmethod
    def _get_min_invalid_n(cls, key, max_tokens):
        # find the min value in min_invalid_n_per_max_tokens
        # whose key is equal or smaller than max_tokens
        return min(
            (value for k, value in cls._min_invalid_n_per_max_tokens.get(key, {}).items() if k <= max_tokens),
            default=None,
        )

    @classmethod
    def _get_region_key(cls, config):
        # get a key for the valid/invalid region corresponding to the given config
        config = cls._pop_subspace(config, always_copy=False)
        return (
            config["model"],
            config.get("prompt", config.get("messages")),
            config.get("stop"),
        )

    @classmethod
    def _update_invalid_n(cls, prune, region_key, max_tokens, num_completions):
        if prune:
            # update invalid n and prune this config
            cls._min_invalid_n_per_max_tokens[region_key] = invalid_n = cls._min_invalid_n_per_max_tokens.get(
                region_key, {}
            )
            invalid_n[max_tokens] = min(num_completions, invalid_n.get(max_tokens, np.inf))

    @classmethod
    def _pop_subspace(cls, config, always_copy=True):
        if "subspace" in config:
            config = config.copy()
            config.update(config.pop("subspace"))
        return config.copy() if always_copy else config

    @classmethod
    def _get_params_for_create(cls, config: Dict) -> Dict:
        """Get the params for the openai api call from a config in the search space."""
        params = cls._pop_subspace(config)
        if cls._prompts:
            params["prompt"] = cls._prompts[config["prompt"]]
        else:
            params["messages"] = cls._messages[config["messages"]]
        if "stop" in params:
            params["stop"] = cls._stops and cls._stops[params["stop"]]
        temperature_or_top_p = params.pop("temperature_or_top_p", None)
        if temperature_or_top_p:
            params.update(temperature_or_top_p)
        if cls._config_list and "config_list" not in params:
            params["config_list"] = cls._config_list
        return params

    @classmethod
    def _eval(cls, config: dict, prune=True, eval_only=False):
        """Evaluate the given config as the hyperparameter setting for the openai api call.

        Args:
            config (dict): Hyperparameter setting for the openai api call.
            prune (bool, optional): Whether to enable pruning. Defaults to True.
            eval_only (bool, optional): Whether to evaluate only
              (ignore the inference budget and do not raise error when a request fails).
              Defaults to False.

        Returns:
            dict: Evaluation results.
        """
        cost = 0
        data = cls.data
        params = cls._get_params_for_create(config)
        model = params["model"]
        data_length = len(data)
        price = cls.price1K.get(model)
        price_input, price_output = price if isinstance(price, tuple) else (price, price)
        inference_budget = getattr(cls, "inference_budget", None)
        prune_hp = getattr(cls, "_prune_hp", "n")
        metric = cls._metric
        config_n = params.get(prune_hp, 1)  # default value in OpenAI is 1
        max_tokens = params.get(
            "max_tokens", np.inf if model in cls.chat_models or issubclass(cls, ChatCompletion) else 16
        )
        target_output_tokens = None
        if not cls.avg_input_tokens:
            input_tokens = [None] * data_length
        prune = prune and inference_budget and not eval_only
        if prune:
            region_key = cls._get_region_key(config)
            max_valid_n = cls._get_max_valid_n(region_key, max_tokens)
            if cls.avg_input_tokens:
                target_output_tokens = (inference_budget * 1000 - cls.avg_input_tokens * price_input) / price_output
                # max_tokens bounds the maximum tokens
                # so using it we can calculate a valid n according to the avg # input tokens
                max_valid_n = max(
                    max_valid_n,
                    int(target_output_tokens // max_tokens),
                )
            if config_n <= max_valid_n:
                start_n = config_n
            else:
                min_invalid_n = cls._get_min_invalid_n(region_key, max_tokens)
                if min_invalid_n is not None and config_n >= min_invalid_n:
                    # prune this config
                    return {
                        "inference_cost": np.inf,
                        metric: np.inf if cls._mode == "min" else -np.inf,
                        "cost": cost,
                    }
                start_n = max_valid_n + 1
        else:
            start_n = config_n
            region_key = None
        num_completions, previous_num_completions = start_n, 0
        n_tokens_list, result, responses_list = [], {}, []
        while True:  # n <= config_n
            params[prune_hp] = num_completions - previous_num_completions
            data_limit = 1 if prune else data_length
            prev_data_limit = 0
            data_early_stop = False  # whether data early stop happens for this n
            while True:  # data_limit <= data_length
                # limit the number of data points to avoid rate limit
                for i in range(prev_data_limit, data_limit):
                    logger.debug(f"num_completions={num_completions}, data instance={i}")
                    data_i = data[i]
                    response = cls.create(data_i, raise_on_ratelimit_or_timeout=eval_only, **params)
                    if response == -1:  # rate limit/timeout error, treat as invalid
                        cls._update_invalid_n(prune, region_key, max_tokens, num_completions)
                        result[metric] = 0
                        result["cost"] = cost
                        return result
                    # evaluate the quality of the responses
                    responses = cls.extract_text_or_function_call(response)
                    usage = response["usage"]
                    n_input_tokens = usage["prompt_tokens"]
                    n_output_tokens = usage.get("completion_tokens", 0)
                    if not cls.avg_input_tokens and not input_tokens[i]:
                        # store the # input tokens
                        input_tokens[i] = n_input_tokens
                    query_cost = response["cost"]
                    cls._total_cost += query_cost
                    cost += query_cost
                    if cls.optimization_budget and cls._total_cost >= cls.optimization_budget and not eval_only:
                        # limit the total tuning cost
                        return {
                            metric: 0,
                            "total_cost": cls._total_cost,
                            "cost": cost,
                        }
                    if previous_num_completions:
                        n_tokens_list[i] += n_output_tokens
                        responses_list[i].extend(responses)
                        # Assumption 1: assuming requesting n1, n2 responses separately then combining them
                        # is the same as requesting (n1+n2) responses together
                    else:
                        n_tokens_list.append(n_output_tokens)
                        responses_list.append(responses)
                avg_n_tokens = np.mean(n_tokens_list[:data_limit])
                rho = (
                    (1 - data_limit / data_length) * (1 + 1 / data_limit)
                    if data_limit << 1 > data_length
                    else (1 - (data_limit - 1) / data_length)
                )
                # Hoeffding-Serfling bound
                ratio = 0.1 * np.sqrt(rho / data_limit)
                if target_output_tokens and avg_n_tokens > target_output_tokens * (1 + ratio) and not eval_only:
                    cls._update_invalid_n(prune, region_key, max_tokens, num_completions)
                    result[metric] = 0
                    result["total_cost"] = cls._total_cost
                    result["cost"] = cost
                    return result
                if (
                    prune
                    and target_output_tokens
                    and avg_n_tokens <= target_output_tokens * (1 - ratio)
                    and (num_completions < config_n or num_completions == config_n and data_limit == data_length)
                ):
                    # update valid n
                    cls._max_valid_n_per_max_tokens[region_key] = valid_n = cls._max_valid_n_per_max_tokens.get(
                        region_key, {}
                    )
                    valid_n[max_tokens] = max(num_completions, valid_n.get(max_tokens, 0))
                    if num_completions < config_n:
                        # valid already, skip the rest of the data
                        data_limit = data_length
                        data_early_stop = True
                        break
                prev_data_limit = data_limit
                if data_limit < data_length:
                    data_limit = min(data_limit << 1, data_length)
                else:
                    break
            # use exponential search to increase n
            if num_completions == config_n:
                for i in range(data_limit):
                    data_i = data[i]
                    responses = responses_list[i]
                    metrics = cls._eval_func(responses, **data_i)
                    if result:
                        for key, value in metrics.items():
                            if isinstance(value, (float, int)):
                                result[key] += value
                    else:
                        result = metrics
                for key in result.keys():
                    if isinstance(result[key], (float, int)):
                        result[key] /= data_limit
                result["total_cost"] = cls._total_cost
                result["cost"] = cost
                if not cls.avg_input_tokens:
                    cls.avg_input_tokens = np.mean(input_tokens)
                    if prune:
                        target_output_tokens = (
                            inference_budget * 1000 - cls.avg_input_tokens * price_input
                        ) / price_output
                result["inference_cost"] = (avg_n_tokens * price_output + cls.avg_input_tokens * price_input) / 1000
                break
            else:
                if data_early_stop:
                    previous_num_completions = 0
                    n_tokens_list.clear()
                    responses_list.clear()
                else:
                    previous_num_completions = num_completions
                num_completions = min(num_completions << 1, config_n)
        return result

    @classmethod
    def tune(
        cls,
        data: List[Dict],
        metric: str,
        mode: str,
        eval_func: Callable,
        log_file_name: Optional[str] = None,
        inference_budget: Optional[float] = None,
        optimization_budget: Optional[float] = None,
        num_samples: Optional[int] = 1,
        logging_level: Optional[int] = logging.WARNING,
        **config,
    ):
        """Tune the parameters for the OpenAI API call.

        TODO: support parallel tuning with ray or spark.
        TODO: support agg_method as in test

        Args:
            data (list): The list of data points.
            metric (str): The metric to optimize.
            mode (str): The optimization mode, "min" or "max.
            eval_func (Callable): The evaluation function for responses.
                The function should take a list of responses and a data point as input,
                and return a dict of metrics. For example,

        ```python
        def eval_func(responses, **data):
            solution = data["solution"]
            success_list = []
            n = len(responses)
            for i in range(n):
                response = responses[i]
                succeed = is_equiv_chain_of_thought(response, solution)
                success_list.append(succeed)
            return {
                "expected_success": 1 - pow(1 - sum(success_list) / n, n),
                "success": any(s for s in success_list),
            }
        ```

            log_file_name (str, optional): The log file.
            inference_budget (float, optional): The inference budget, dollar per instance.
            optimization_budget (float, optional): The optimization budget, dollar in total.
            num_samples (int, optional): The number of samples to evaluate.
                -1 means no hard restriction in the number of trials
                and the actual number is decided by optimization_budget. Defaults to 1.
            logging_level (optional): logging level. Defaults to logging.WARNING.
            **config (dict): The search space to update over the default search.
                For prompt, please provide a string/Callable or a list of strings/Callables.
                    - If prompt is provided for chat models, it will be converted to messages under role "user".
                    - Do not provide both prompt and messages for chat models, but provide either of them.
                    - A string template will be used to generate a prompt for each data instance
                      using `prompt.format(**data)`.
                    - A callable template will be used to generate a prompt for each data instance
                      using `prompt(data)`.
                For stop, please provide a string, a list of strings, or a list of lists of strings.
                For messages (chat models only), please provide a list of messages (for a single chat prefix)
                or a list of lists of messages (for multiple choices of chat prefix to choose from).
                Each message should be a dict with keys "role" and "content". The value of "content" can be a string/Callable template.

        Returns:
            dict: The optimized hyperparameter setting.
            tune.ExperimentAnalysis: The tuning results.
        """
        logger.warning(
            "tuning via Completion.tune is deprecated in pyautogen v0.2 and openai>=1. "
            "flaml.tune supports tuning more generically."
        )
        if ERROR:
            raise ERROR
        space = cls.default_search_space.copy()
        if config is not None:
            space.update(config)
            if "messages" in space:
                space.pop("prompt", None)
            temperature = space.pop("temperature", None)
            top_p = space.pop("top_p", None)
            if temperature is not None and top_p is None:
                space["temperature_or_top_p"] = {"temperature": temperature}
            elif temperature is None and top_p is not None:
                space["temperature_or_top_p"] = {"top_p": top_p}
            elif temperature is not None and top_p is not None:
                space.pop("temperature_or_top_p")
                space["temperature"] = temperature
                space["top_p"] = top_p
                logger.warning("temperature and top_p are not recommended to vary together.")
        cls._max_valid_n_per_max_tokens, cls._min_invalid_n_per_max_tokens = {}, {}
        cls.optimization_budget = optimization_budget
        cls.inference_budget = inference_budget
        cls._prune_hp = "best_of" if space.get("best_of", 1) != 1 else "n"
        cls._prompts = space.get("prompt")
        if cls._prompts is None:
            cls._messages = space.get("messages")
            if not all((isinstance(cls._messages, list), isinstance(cls._messages[0], (dict, list)))):
                error_msg = "messages must be a list of dicts or a list of lists."
                logger.error(error_msg)
                raise AssertionError(error_msg)
            if isinstance(cls._messages[0], dict):
                cls._messages = [cls._messages]
            space["messages"] = tune.choice(list(range(len(cls._messages))))
        else:
            if space.get("messages") is not None:
                error_msg = "messages and prompt cannot be provided at the same time."
                logger.error(error_msg)
                raise AssertionError(error_msg)
            if not isinstance(cls._prompts, (str, list)):
                error_msg = "prompt must be a string or a list of strings."
                logger.error(error_msg)
                raise AssertionError(error_msg)
            if isinstance(cls._prompts, str):
                cls._prompts = [cls._prompts]
            space["prompt"] = tune.choice(list(range(len(cls._prompts))))
        cls._stops = space.get("stop")
        if cls._stops:
            if not isinstance(cls._stops, (str, list)):
                error_msg = "stop must be a string, a list of strings, or a list of lists of strings."
                logger.error(error_msg)
                raise AssertionError(error_msg)
            if not (isinstance(cls._stops, list) and isinstance(cls._stops[0], list)):
                cls._stops = [cls._stops]
            space["stop"] = tune.choice(list(range(len(cls._stops))))
        cls._config_list = space.get("config_list")
        if cls._config_list is not None:
            is_const = is_constant(cls._config_list)
            if is_const:
                space.pop("config_list")
        cls._metric, cls._mode = metric, mode
        cls._total_cost = 0  # total optimization cost
        cls._eval_func = eval_func
        cls.data = data
        cls.avg_input_tokens = None

        space_model = space["model"]
        if not isinstance(space_model, str) and len(space_model) > 1:
            # make a hierarchical search space
            subspace = {}
            if "max_tokens" in space:
                subspace["max_tokens"] = space.pop("max_tokens")
            if "temperature_or_top_p" in space:
                subspace["temperature_or_top_p"] = space.pop("temperature_or_top_p")
            if "best_of" in space:
                subspace["best_of"] = space.pop("best_of")
            if "n" in space:
                subspace["n"] = space.pop("n")
            choices = []
            for model in space["model"]:
                choices.append({"model": model, **subspace})
            space["subspace"] = tune.choice(choices)
            space.pop("model")
            # start all the models with the same hp config
            search_alg = BlendSearch(
                cost_attr="cost",
                cost_budget=optimization_budget,
                metric=metric,
                mode=mode,
                space=space,
            )
            config0 = search_alg.suggest("t0")
            points_to_evaluate = [config0]
            for model in space_model:
                if model != config0["subspace"]["model"]:
                    point = config0.copy()
                    point["subspace"] = point["subspace"].copy()
                    point["subspace"]["model"] = model
                    points_to_evaluate.append(point)
            search_alg = BlendSearch(
                cost_attr="cost",
                cost_budget=optimization_budget,
                metric=metric,
                mode=mode,
                space=space,
                points_to_evaluate=points_to_evaluate,
            )
        else:
            search_alg = BlendSearch(
                cost_attr="cost",
                cost_budget=optimization_budget,
                metric=metric,
                mode=mode,
                space=space,
            )
        old_level = logger.getEffectiveLevel()
        logger.setLevel(logging_level)
        with diskcache.Cache(cls.cache_path) as cls._cache:
            analysis = tune.run(
                cls._eval,
                search_alg=search_alg,
                num_samples=num_samples,
                log_file_name=log_file_name,
                verbose=3,
            )
        config = analysis.best_config
        params = cls._get_params_for_create(config)
        if cls._config_list is not None and is_const:
            params.pop("config_list")
        logger.setLevel(old_level)
        return params, analysis

    @classmethod
    def create(
        cls,
        context: Optional[Dict] = None,
        use_cache: Optional[bool] = True,
        config_list: Optional[List[Dict]] = None,
        filter_func: Optional[Callable[[Dict, Dict], bool]] = None,
        raise_on_ratelimit_or_timeout: Optional[bool] = True,
        allow_format_str_template: Optional[bool] = False,
        **config,
    ):
        """Make a completion for a given context.

        Args:
            context (Dict, Optional): The context to instantiate the prompt.
                It needs to contain keys that are used by the prompt template or the filter function.
                E.g., `prompt="Complete the following sentence: {prefix}, context={"prefix": "Today I feel"}`.
                The actual prompt will be:
                "Complete the following sentence: Today I feel".
                More examples can be found at [templating](https://microsoft.github.io/autogen/docs/Use-Cases/enhanced_inference#templating).
            use_cache (bool, Optional): Whether to use cached responses.
            config_list (List, Optional): List of configurations for the completion to try.
                The first one that does not raise an error will be used.
                Only the differences from the default config need to be provided.
                E.g.,

        ```python
        response = oai.Completion.create(
            config_list=[
                {
                    "model": "gpt-4",
                    "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
                    "api_type": "azure",
                    "base_url": os.environ.get("AZURE_OPENAI_API_BASE"),
                    "api_version": "2024-02-01",
                },
                {
                    "model": "gpt-3.5-turbo",
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                    "api_type": "openai",
                    "base_url": "https://api.openai.com/v1",
                },
                {
                    "model": "llama-7B",
                    "base_url": "http://127.0.0.1:8080",
                    "api_type": "openai",
                }
            ],
            prompt="Hi",
        )
        ```

            filter_func (Callable, Optional): A function that takes in the context and the response and returns a boolean to indicate whether the response is valid. E.g.,

        ```python
        def yes_or_no_filter(context, config, response):
            return context.get("yes_or_no_choice", False) is False or any(
                text in ["Yes.", "No."] for text in oai.Completion.extract_text(response)
            )
        ```

            raise_on_ratelimit_or_timeout (bool, Optional): Whether to raise RateLimitError or Timeout when all configs fail.
                When set to False, -1 will be returned when all configs fail.
            allow_format_str_template (bool, Optional): Whether to allow format string template in the config.
            **config: Configuration for the openai API call. This is used as parameters for calling openai API.
                The "prompt" or "messages" parameter can contain a template (str or Callable) which will be instantiated with the context.
                Besides the parameters for the openai API call, it can also contain:
                - `max_retry_period` (int): the total time (in seconds) allowed for retrying failed requests.
                - `retry_wait_time` (int): the time interval to wait (in seconds) before retrying a failed request.
                - `cache_seed` (int) for the cache. This is useful when implementing "controlled randomness" for the completion.

        Returns:
            Responses from OpenAI API, with additional fields.
                - `cost`: the total cost.
            When `config_list` is provided, the response will contain a few more fields:
                - `config_id`: the index of the config in the config_list that is used to generate the response.
                - `pass_filter`: whether the response passes the filter function. None if no filter is provided.
        """
        logger.warning(
            "Completion.create is deprecated in pyautogen v0.2 and openai>=1. "
            "The new openai requires initiating a client for inference. "
            "Please refer to https://microsoft.github.io/autogen/docs/Use-Cases/enhanced_inference#api-unification"
        )
        if ERROR:
            raise ERROR

        # Warn if a config list was provided but was empty
        if isinstance(config_list, list) and len(config_list) == 0:
            logger.warning(
                "Completion was provided with a config_list, but the list was empty. Adopting default OpenAI behavior, which reads from the 'model' parameter instead."
            )

        if config_list:
            last = len(config_list) - 1
            cost = 0
            for i, each_config in enumerate(config_list):
                base_config = config.copy()
                base_config["allow_format_str_template"] = allow_format_str_template
                base_config.update(each_config)
                if i < last and filter_func is None and "max_retry_period" not in base_config:
                    # max_retry_period = 0 to avoid retrying when no filter is given
                    base_config["max_retry_period"] = 0
                try:
                    response = cls.create(
                        context,
                        use_cache,
                        raise_on_ratelimit_or_timeout=i < last or raise_on_ratelimit_or_timeout,
                        **base_config,
                    )
                    if response == -1:
                        return response
                    pass_filter = filter_func is None or filter_func(context=context, response=response)
                    if pass_filter or i == last:
                        response["cost"] = cost + response["cost"]
                        response["config_id"] = i
                        response["pass_filter"] = pass_filter
                        return response
                    cost += response["cost"]
                except (AuthenticationError, RateLimitError, Timeout, BadRequestError):
                    logger.debug(f"failed with config {i}", exc_info=1)
                    if i == last:
                        raise
        params = cls._construct_params(context, config, allow_format_str_template=allow_format_str_template)
        if not use_cache:
            return cls._get_response(
                params, raise_on_ratelimit_or_timeout=raise_on_ratelimit_or_timeout, use_cache=False
            )
        cache_seed = cls.cache_seed
        if "cache_seed" in params:
            cls.set_cache(params.pop("cache_seed"))
        with diskcache.Cache(cls.cache_path) as cls._cache:
            cls.set_cache(cache_seed)
            return cls._get_response(params, raise_on_ratelimit_or_timeout=raise_on_ratelimit_or_timeout)

    @classmethod
    def instantiate(
        cls,
        template: Union[str, None],
        context: Optional[Dict] = None,
        allow_format_str_template: Optional[bool] = False,
    ):
        if not context or template is None:
            return template
        if isinstance(template, str):
            return template.format(**context) if allow_format_str_template else template
        return template(context)

    @classmethod
    def _construct_params(cls, context, config, prompt=None, messages=None, allow_format_str_template=False):
        params = config.copy()
        model = config["model"]
        prompt = config.get("prompt") if prompt is None else prompt
        messages = config.get("messages") if messages is None else messages
        # either "prompt" should be in config (for being compatible with non-chat models)
        # or "messages" should be in config (for tuning chat models only)
        if prompt is None and (model in cls.chat_models or issubclass(cls, ChatCompletion)):
            if messages is None:
                raise ValueError("Either prompt or messages should be in config for chat models.")
        if prompt is None:
            params["messages"] = (
                [
                    (
                        {
                            **m,
                            "content": cls.instantiate(m["content"], context, allow_format_str_template),
                        }
                        if m.get("content")
                        else m
                    )
                    for m in messages
                ]
                if context
                else messages
            )
        elif model in cls.chat_models or issubclass(cls, ChatCompletion):
            # convert prompt to messages
            params["messages"] = [
                {
                    "role": "user",
                    "content": cls.instantiate(prompt, context, allow_format_str_template),
                },
            ]
            params.pop("prompt", None)
        else:
            params["prompt"] = cls.instantiate(prompt, context, allow_format_str_template)
        return params

    @classmethod
    def test(
        cls,
        data,
        eval_func=None,
        use_cache=True,
        agg_method="avg",
        return_responses_and_per_instance_result=False,
        logging_level=logging.WARNING,
        **config,
    ):
        """Evaluate the responses created with the config for the OpenAI API call.

        Args:
            data (list): The list of test data points.
            eval_func (Callable): The evaluation function for responses per data instance.
                The function should take a list of responses and a data point as input,
                and return a dict of metrics. You need to either provide a valid callable
                eval_func; or do not provide one (set None) but call the test function after
                calling the tune function in which a eval_func is provided.
                In the latter case we will use the eval_func provided via tune function.
                Defaults to None.

        ```python
        def eval_func(responses, **data):
            solution = data["solution"]
            success_list = []
            n = len(responses)
            for i in range(n):
                response = responses[i]
                succeed = is_equiv_chain_of_thought(response, solution)
                success_list.append(succeed)
            return {
                "expected_success": 1 - pow(1 - sum(success_list) / n, n),
                "success": any(s for s in success_list),
            }
        ```
            use_cache (bool, Optional): Whether to use cached responses. Defaults to True.
            agg_method (str, Callable or a dict of Callable): Result aggregation method (across
                multiple instances) for each of the metrics. Defaults to 'avg'.
                An example agg_method in str:

        ```python
        agg_method = 'median'
        ```
                An example agg_method in a Callable:

        ```python
        agg_method = np.median
        ```

                An example agg_method in a dict of Callable:

        ```python
        agg_method={'median_success': np.median, 'avg_success': np.mean}
        ```

            return_responses_and_per_instance_result (bool): Whether to also return responses
                and per instance results in addition to the aggregated results.
            logging_level (optional): logging level. Defaults to logging.WARNING.
            **config (dict): parameters passed to the openai api call `create()`.

        Returns:
            None when no valid eval_func is provided in either test or tune;
            Otherwise, a dict of aggregated results, responses and per instance results if `return_responses_and_per_instance_result` is True;
            Otherwise, a dict of aggregated results (responses and per instance results are not returned).
        """
        result_agg, responses_list, result_list = {}, [], []
        metric_keys = None
        cost = 0
        old_level = logger.getEffectiveLevel()
        logger.setLevel(logging_level)
        for i, data_i in enumerate(data):
            logger.info(f"evaluating data instance {i}")
            response = cls.create(data_i, use_cache, **config)
            cost += response["cost"]
            # evaluate the quality of the responses
            responses = cls.extract_text_or_function_call(response)
            if eval_func is not None:
                metrics = eval_func(responses, **data_i)
            elif hasattr(cls, "_eval_func"):
                metrics = cls._eval_func(responses, **data_i)
            else:
                logger.warning(
                    "Please either provide a valid eval_func or do the test after the tune function is called."
                )
                return
            if not metric_keys:
                metric_keys = []
                for k in metrics.keys():
                    try:
                        _ = float(metrics[k])
                        metric_keys.append(k)
                    except ValueError:
                        pass
            result_list.append(metrics)
            if return_responses_and_per_instance_result:
                responses_list.append(responses)
        if isinstance(agg_method, str):
            if agg_method in ["avg", "average"]:
                for key in metric_keys:
                    result_agg[key] = np.mean([r[key] for r in result_list])
            elif agg_method == "median":
                for key in metric_keys:
                    result_agg[key] = np.median([r[key] for r in result_list])
            else:
                logger.warning(
                    f"Aggregation method {agg_method} not supported. Please write your own aggregation method as a callable(s)."
                )
        elif callable(agg_method):
            for key in metric_keys:
                result_agg[key] = agg_method([r[key] for r in result_list])
        elif isinstance(agg_method, dict):
            for key in metric_keys:
                metric_agg_method = agg_method[key]
                if not callable(metric_agg_method):
                    error_msg = "please provide a callable for each metric"
                    logger.error(error_msg)
                    raise AssertionError(error_msg)
                result_agg[key] = metric_agg_method([r[key] for r in result_list])
        else:
            raise ValueError(
                "agg_method needs to be a string ('avg' or 'median'),\
                or a callable, or a dictionary of callable."
            )
        logger.setLevel(old_level)
        # should we also return the result_list and responses_list or not?
        if "cost" not in result_agg:
            result_agg["cost"] = cost
        if "inference_cost" not in result_agg:
            result_agg["inference_cost"] = cost / len(data)
        if return_responses_and_per_instance_result:
            return result_agg, result_list, responses_list
        else:
            return result_agg

    @classmethod
    def cost(cls, response: dict):
        """Compute the cost of an API call.

        Args:
            response (dict): The response from OpenAI API.

        Returns:
            The cost in USD. 0 if the model is not supported.
        """
        model = response.get("model")
        if model not in cls.price1K:
            return 0
            # raise ValueError(f"Unknown model: {model}")
        usage = response["usage"]
        n_input_tokens = usage["prompt_tokens"]
        n_output_tokens = usage.get("completion_tokens", 0)
        price1K = cls.price1K[model]
        if isinstance(price1K, tuple):
            return (price1K[0] * n_input_tokens + price1K[1] * n_output_tokens) / 1000
        return price1K * (n_input_tokens + n_output_tokens) / 1000

    @classmethod
    def extract_text(cls, response: dict) -> List[str]:
        """Extract the text from a completion or chat response.

        Args:
            response (dict): The response from OpenAI API.

        Returns:
            A list of text in the responses.
        """
        choices = response["choices"]
        if "text" in choices[0]:
            return [choice["text"] for choice in choices]
        return [choice["message"].get("content", "") for choice in choices]

    @classmethod
    def extract_text_or_function_call(cls, response: dict) -> List[str]:
        """Extract the text or function calls from a completion or chat response.

        Args:
            response (dict): The response from OpenAI API.

        Returns:
            A list of text or function calls in the responses.
        """
        choices = response["choices"]
        if "text" in choices[0]:
            return [choice["text"] for choice in choices]
        return [
            choice["message"] if "function_call" in choice["message"] else choice["message"].get("content", "")
            for choice in choices
        ]

    @classmethod
    @property
    def logged_history(cls) -> Dict:
        """Return the book keeping dictionary."""
        return cls._history_dict

    @classmethod
    def print_usage_summary(cls) -> Dict:
        """Return the usage summary."""
        if cls._history_dict is None:
            print("No usage summary available.", flush=True)

        token_count_summary = defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

        if not cls._history_compact:
            source = cls._history_dict.values()
            total_cost = sum(msg_pair["response"]["cost"] for msg_pair in source)
        else:
            # source = cls._history_dict["token_count"]
            # total_cost = sum(cls._history_dict['cost'])
            total_cost = sum(sum(value_list["cost"]) for value_list in cls._history_dict.values())
            source = (
                token_data for value_list in cls._history_dict.values() for token_data in value_list["token_count"]
            )

        for entry in source:
            if not cls._history_compact:
                model = entry["response"]["model"]
                token_data = entry["response"]["usage"]
            else:
                model = entry["model"]
                token_data = entry

            token_count_summary[model]["prompt_tokens"] += token_data["prompt_tokens"]
            token_count_summary[model]["completion_tokens"] += token_data["completion_tokens"]
            token_count_summary[model]["total_tokens"] += token_data["total_tokens"]

        print(f"Total cost: {total_cost}", flush=True)
        for model, counts in token_count_summary.items():
            print(
                f"Token count summary for model {model}: prompt_tokens: {counts['prompt_tokens']}, completion_tokens: {counts['completion_tokens']}, total_tokens: {counts['total_tokens']}",
                flush=True,
            )

    @classmethod
    def start_logging(
        cls, history_dict: Optional[Dict] = None, compact: Optional[bool] = True, reset_counter: Optional[bool] = True
    ):
        """Start book keeping.

        Args:
            history_dict (Dict): A dictionary for book keeping.
                If no provided, a new one will be created.
            compact (bool): Whether to keep the history dictionary compact.
                Compact history contains one key per conversation, and the value is a dictionary
                like:
        ```python
        {
            "create_at": [0, 1],
            "cost": [0.1, 0.2],
        }
        ```
                where "created_at" is the index of API calls indicating the order of all the calls,
                and "cost" is the cost of each call. This example shows that the conversation is based
                on two API calls. The compact format is useful for condensing the history of a conversation.
                If compact is False, the history dictionary will contain all the API calls: the key
                is the index of the API call, and the value is a dictionary like:
        ```python
        {
            "request": request_dict,
            "response": response_dict,
        }
        ```
                where request_dict is the request sent to OpenAI API, and response_dict is the response.
                For a conversation containing two API calls, the non-compact history dictionary will be like:
        ```python
        {
            0: {
                "request": request_dict_0,
                "response": response_dict_0,
            },
            1: {
                "request": request_dict_1,
                "response": response_dict_1,
            },
        ```
                The first request's messages plus the response is equal to the second request's messages.
                For a conversation with many turns, the non-compact history dictionary has a quadratic size
                while the compact history dict has a linear size.
            reset_counter (bool): whether to reset the counter of the number of API calls.
        """
        logger.warning(
            "logging via Completion.start_logging is deprecated in pyautogen v0.2. "
            "logging via OpenAIWrapper will be added back in a future release."
        )
        if ERROR:
            raise ERROR
        cls._history_dict = {} if history_dict is None else history_dict
        cls._history_compact = compact
        cls._count_create = 0 if reset_counter or cls._count_create is None else cls._count_create

    @classmethod
    def stop_logging(cls):
        """End book keeping."""
        cls._history_dict = cls._count_create = None


class ChatCompletion(Completion):
    """(openai<1) A class for OpenAI API ChatCompletion. Share the same API as Completion."""

    default_search_space = Completion.default_search_space.copy()
    default_search_space["model"] = tune.choice(["gpt-3.5-turbo", "gpt-4"])
    openai_completion_class = not ERROR and openai.ChatCompletion
