from time import sleep
import logging
import numpy as np
import time
from flaml import tune, BlendSearch

try:
    import openai
    from openai.error import (
        ServiceUnavailableError,
        RateLimitError,
        APIError,
        InvalidRequestError,
        APIConnectionError,
        Timeout,
    )
    import diskcache

    ERROR = None
except ImportError:
    ERROR = ImportError(
        "please install flaml[openai] option to use the flaml.oai subpackage."
    )
logger = logging.getLogger(__name__)


def get_key(config):
    """Get a unique identifier of a configuration.

    Args:
        config (dict or list): A configuration.

    Returns:
        tuple: A unique identifier which can be used as a key for a dict.
    """
    if isinstance(config, dict):
        return tuple(get_key(x) for x in sorted(config.items()))
    if isinstance(config, list):
        return tuple(get_key(x) for x in config)
    return config


class Completion:
    """A class for OpenAI completion API.

    It also supports: ChatCompletion, Azure OpenAI API.
    """

    # set of models that support chat completion
    chat_models = {
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0301",
        "gpt-4",
        "gpt-4-32k",
        "gpt-4-32k-0314",
        "gpt-4-0314",
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
        "gpt-3.5-turbo": 0.002,
        "gpt-3.5-turbo-0301": 0.002,
        "gpt-4": (0.03, 0.06),
        "gpt-4-0314": (0.03, 0.06),
        "gpt-4-32k": (0.06, 0.12),
        "gpt-4-32k-0314": (0.06, 0.12),
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
                {"temperature": tune.uniform(0, 1)},
                {"top_p": tune.uniform(0, 1)},
            ]
        ),
        "max_tokens": tune.lograndint(50, 1000),
        "n": tune.randint(1, 100),
        "prompt": "{prompt}",
    }

    seed = 41
    # retry after this many seconds
    retry_time = 10
    # fail a request after hitting RateLimitError for this many seconds
    retry_timeout = 60
    # time out for request to openai server
    request_timeout = 30

    openai_completion_class = not ERROR and openai.Completion
    _total_cost = 0
    optimization_budget = None

    @classmethod
    def set_cache(cls, seed=41, cache_path=".cache"):
        """Set cache path.

        Args:
            seed (int, Optional): The integer identifier for the pseudo seed.
                Results corresponding to different seeds will be cached in different places.
            cache_path (str, Optional): The root path for the cache.
                The complete cache path will be {cache_path}/{seed}.
        """
        cls.seed = seed
        cls.cache_path = f"{cache_path}/{seed}"

    @classmethod
    def _get_response(cls, config: dict, eval_only=False, use_cache=True):
        """Get the response from the openai api call.

        Try cache first. If not found, call the openai api. If the api call fails, retry after retry_time.
        """
        key = get_key(config)
        if use_cache:
            response = cls._cache.get(key, None)
            if response is not None and (response != -1 or not eval_only):
                # print("using cached response")
                return response
        openai_completion = (
            openai.ChatCompletion
            if config["model"] in cls.chat_models
            else openai.Completion
        )
        start_time = time.time()
        while True:
            try:
                response = openai_completion.create(
                    request_timeout=cls.request_timeout, **config
                )
                cls._cache.set(key, response)
                return response
            except (
                ServiceUnavailableError,
                APIError,
                APIConnectionError,
            ):
                # transient error
                logger.warning(f"retrying in {cls.retry_time} seconds...", exc_info=1)
                sleep(cls.retry_time)
            except (RateLimitError, Timeout):
                # retry after retry_time seconds
                if time.time() - start_time + cls.retry_time < cls.retry_timeout:
                    logger.info(f"retrying in {cls.retry_time} seconds...", exc_info=1)
                elif not eval_only:
                    break
                sleep(cls.retry_time)
            except InvalidRequestError:
                if "azure" == openai.api_type and "model" in config:
                    # azure api uses "engine" instead of "model"
                    config = config.copy()
                    config["engine"] = config.pop("model")
                else:
                    raise
        logger.warning(
            f"Failed to get response from openai api due to getting RateLimitError or Timeout for {cls.retry_timeout} seconds."
        )
        response = -1
        cls._cache.set(key, response)
        return response

    @classmethod
    def _get_max_valid_n(cls, key, max_tokens):
        # find the max value in max_valid_n_per_max_tokens
        # whose key is equal or larger than max_tokens
        return max(
            (
                value
                for k, value in cls._max_valid_n_per_max_tokens.get(key, {}).items()
                if k >= max_tokens
            ),
            default=1,
        )

    @classmethod
    def _get_min_invalid_n(cls, key, max_tokens):
        # find the min value in min_invalid_n_per_max_tokens
        # whose key is equal or smaller than max_tokens
        return min(
            (
                value
                for k, value in cls._min_invalid_n_per_max_tokens.get(key, {}).items()
                if k <= max_tokens
            ),
            default=None,
        )

    @classmethod
    def _get_region_key(cls, config):
        # get a key for the valid/invalid region corresponding to the given config
        return (
            config["model"],
            config.get("prompt", config.get("messages")),
            config.get("stop"),
        )

    @classmethod
    def _update_invalid_n(cls, prune, region_key, max_tokens, num_completions):
        if prune:
            # update invalid n and prune this config
            cls._min_invalid_n_per_max_tokens[
                region_key
            ] = invalid_n = cls._min_invalid_n_per_max_tokens.get(region_key, {})
            invalid_n[max_tokens] = min(
                num_completions, invalid_n.get(max_tokens, np.inf)
            )

    @classmethod
    def _get_prompt_messages_from_config(cls, model, config):
        prompt, messages = None, None
        if model in cls.chat_models:
            # either "prompt" should be in config (for being compatible with non-chat models)
            # or "messages" should be in config (for tuning chat models only)
            prompt = config.get("prompt")
            messages = config.get("messages")
            # either prompt or messages should be in config, but not both
            assert (prompt is None) != (
                messages is None
            ), "Either prompt or messages should be in config for chat models."
            if prompt is None:
                messages = cls._messages[messages]
            else:
                prompt = cls._prompts[prompt]
        else:
            prompt = cls._prompts[config["prompt"]]
        return prompt, messages

    @classmethod
    def _eval(cls, config: dict, prune=True, eval_only=False):
        """Evaluate the given config as the hyperparameter setting for the openai api call.

        Args:
            config (dict): Hyperparameter setting for the openai api call.
            prune (bool, optional): Whether to enable pruning. Defaults to True.
            eval_only (bool, optional): Whether to evaluate only (ignore the inference budget and no timeout).
              Defaults to False.

        Returns:
            dict: Evaluation results.
        """
        cost = 0
        data = cls.data
        model = config["model"]
        data_length = len(data)
        price = cls.price1K.get(model)
        price_input, price_output = (
            price if isinstance(price, tuple) else (price, price)
        )
        inference_budget = getattr(cls, "inference_budget", None)
        prune_hp = getattr(cls, "_prune_hp", "n")
        metric = cls._metric
        config_n = config.get(prune_hp, 1)  # default value in OpenAI is 1
        max_tokens = config.get(
            "max_tokens", np.inf if model in cls.chat_models else 16
        )
        prompt, messages = cls._get_prompt_messages_from_config(model, config)
        stop = cls._stops and cls._stops[config["stop"]]
        target_output_tokens = None
        if not cls.avg_input_tokens:
            input_tokens = [None] * data_length
        prune = prune and inference_budget and not eval_only
        if prune:
            region_key = cls._get_region_key(config)
            max_valid_n = cls._get_max_valid_n(region_key, max_tokens)
            if cls.avg_input_tokens:
                target_output_tokens = (
                    inference_budget * 1000 - cls.avg_input_tokens * price_input
                ) / price_output
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
        params = config.copy()
        params["stop"] = stop
        temperature_or_top_p = params.pop("temperature_or_top_p", None)
        if temperature_or_top_p:
            params.update(temperature_or_top_p)
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
                    logger.debug(
                        f"num_completions={num_completions}, data instance={i}"
                    )
                    data_i = data[i]
                    params = cls._construct_params(data_i, params, prompt, messages)
                    response = cls._get_response(params, eval_only)
                    if response == -1:  # rate limit error, treat as invalid
                        cls._update_invalid_n(
                            prune, region_key, max_tokens, num_completions
                        )
                        result[metric] = 0
                        result["cost"] = cost
                        return result
                    # evaluate the quality of the responses
                    responses = (
                        [r["message"]["content"].rstrip() for r in response["choices"]]
                        if model in cls.chat_models
                        else [r["text"].rstrip() for r in response["choices"]]
                    )
                    usage = response["usage"]
                    n_input_tokens = usage["prompt_tokens"]
                    n_output_tokens = usage.get("completion_tokens", 0)
                    if not cls.avg_input_tokens and not input_tokens[i]:
                        # store the # input tokens
                        input_tokens[i] = n_input_tokens
                    query_cost = (
                        price_input * n_input_tokens + price_output * n_output_tokens
                    ) / 1000
                    cls._total_cost += query_cost
                    cost += query_cost
                    if (
                        cls.optimization_budget
                        and cls._total_cost >= cls.optimization_budget
                        and not eval_only
                    ):
                        # limit the total tuning cost
                        return {
                            metric: 0,
                            "total_cost": cls._total_cost,
                            "cost": cost,
                        }
                    if previous_num_completions:
                        n_tokens_list[i] += n_output_tokens
                        responses_list[i].extend(responses)
                        # Assumption 1: assuming requesting n1, n2 responses separatively then combining them
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
                if (
                    target_output_tokens
                    and avg_n_tokens > target_output_tokens * (1 + ratio)
                    and not eval_only
                ):
                    cls._update_invalid_n(
                        prune, region_key, max_tokens, num_completions
                    )
                    result[metric] = 0
                    result["total_cost"] = cls._total_cost
                    result["cost"] = cost
                    return result
                if (
                    prune
                    and target_output_tokens
                    and avg_n_tokens <= target_output_tokens * (1 - ratio)
                    and (
                        num_completions < config_n
                        or num_completions == config_n
                        and data_limit == data_length
                    )
                ):
                    # update valid n
                    cls._max_valid_n_per_max_tokens[
                        region_key
                    ] = valid_n = cls._max_valid_n_per_max_tokens.get(region_key, {})
                    valid_n[max_tokens] = max(
                        num_completions, valid_n.get(max_tokens, 0)
                    )
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
                result["inference_cost"] = (
                    avg_n_tokens * price_output + cls.avg_input_tokens * price_input
                ) / 1000
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
        data,
        metric,
        mode,
        eval_func,
        log_file_name=None,
        inference_budget=None,
        optimization_budget=None,
        num_samples=1,
        logging_level=logging.WARNING,
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
            inference_budget (float, optional): The inference budget.
            optimization_budget (float, optional): The optimization budget.
            num_samples (int, optional): The number of samples to evaluate.
                -1 means no hard restriction in the number of trials
                and the actual number is decided by optimization_budget. Defaults to 1.
            **config (dict): The search space to update over the default search.
                For prompt, please provide a string/Callable or a list of strings/Callables.
                    - If prompt is provided for chat models, it will be converted to messages under role "user".
                    - Do not provide both prompt and messages for chat models, but provide either of them.
                    - A string `prompt` template will be used to generate a prompt for each data instance
                      using `prompt.format(**data)`.
                    - A callable `prompt` template will be used to generate a prompt for each data instance
                      using `prompt(data)`.
                For stop, please provide a string, a list of strings, or a list of lists of strings.
                For messages (chat models only), please provide a list of messages (for a single chat prefix)
                or a list of lists of messages (for multiple choices of chat prefix to choose from).
                Each message should be a dict with keys "role" and "content".

        Returns:
            dict: The optimized hyperparameter setting.
            tune.ExperimentAnalysis: The tuning results.
        """
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
                logger.warning(
                    "temperature and top_p are not recommended to vary together."
                )
        cls._max_valid_n_per_max_tokens, cls._min_invalid_n_per_max_tokens = {}, {}
        cls.optimization_budget = optimization_budget
        cls.inference_budget = inference_budget
        cls._prune_hp = "best_of" if space.get("best_of", 1) != 1 else "n"
        cls._prompts = space.get("prompt")
        if cls._prompts is None:
            cls._messages = space.get("messages")
            assert isinstance(cls._messages, list) and isinstance(
                cls._messages[0], (dict, list)
            ), "messages must be a list of dicts or a list of lists."
            if isinstance(cls._messages[0], dict):
                cls._messages = [cls._messages]
            space["messages"] = tune.choice(list(range(len(cls._messages))))
        else:
            assert (
                space.get("messages") is None
            ), "messages and prompt cannot be provided at the same time."
            assert isinstance(
                cls._prompts, (str, list)
            ), "prompt must be a string or a list of strings."
            if isinstance(cls._prompts, str):
                cls._prompts = [cls._prompts]
            space["prompt"] = tune.choice(list(range(len(cls._prompts))))
        cls._stops = space.get("stop")
        if cls._stops:
            assert isinstance(
                cls._stops, (str, list)
            ), "stop must be a string, a list of strings, or a list of lists of strings."
            if not (isinstance(cls._stops, list) and isinstance(cls._stops[0], list)):
                cls._stops = [cls._stops]
            space["stop"] = tune.choice(list(range(len(cls._stops))))
        cls._metric, cls._mode = metric, mode
        cls._total_cost = 0  # total optimization cost
        cls._eval_func = eval_func
        cls.data = data
        cls.avg_input_tokens = None

        search_alg = BlendSearch(
            cost_attr="cost",
            cost_budget=optimization_budget,
            metric=metric,
            mode=mode,
            space=space,
        )
        space_model = space["model"]
        if not isinstance(space_model, str) and len(space_model) > 1:
            # start all the models with the same hp config
            config0 = search_alg.suggest("t0")
            points_to_evaluate = [config0]
            for model in space_model:
                if model != config0["model"]:
                    point = config0.copy()
                    point["model"] = model
                    points_to_evaluate.append(point)
            search_alg = BlendSearch(
                cost_attr="cost",
                cost_budget=optimization_budget,
                metric=metric,
                mode=mode,
                space=space,
                points_to_evaluate=points_to_evaluate,
            )
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
        params = config.copy()
        if cls._prompts:
            params["prompt"] = cls._prompts[config["prompt"]]
        else:
            params["messages"] = cls._messages[config["messages"]]
        stop = cls._stops and cls._stops[config["stop"]]
        params["stop"] = stop
        temperature_or_top_p = params.pop("temperature_or_top_p", None)
        if temperature_or_top_p:
            params.update(temperature_or_top_p)
        return params, analysis

    @classmethod
    def create(cls, context, use_cache=True, **config):
        """Make a completion for a given context.

        Args:
            context (dict): The context to instantiate the prompt.
                It needs to contain keys that are used by the prompt template.
                E.g., `prompt="Complete the following sentence: {prefix}"`.
                `context={"prefix": "Today I feel"}`.
                The actual prompt sent to OpenAI will be:
                "Complete the following sentence: Today I feel".
            use_cache (bool, Optional): Whether to use cached responses.

        Returns:
            Responses from OpenAI API.
        """
        if ERROR:
            raise ERROR
        params = cls._construct_params(context, config)
        if use_cache:
            with diskcache.Cache(cls.cache_path) as cls._cache:
                return cls._get_response(params)
        return cls.openai_completion_class.create(
            request_timeout=cls.request_timeout, **params
        )

    @classmethod
    def _construct_params(cls, data_instance, config, prompt=None, messages=None):
        params = config.copy()
        model = config["model"]
        prompt = config.get("prompt") if prompt is None else prompt
        messages = config.get("messages") if messages is None else messages
        # either "prompt" should be in config (for being compatible with non-chat models)
        # or "messages" should be in config (for tuning chat models only)
        if prompt is None and model in cls.chat_models:
            if messages is None:
                raise ValueError(
                    "Either prompt or messages should be in config for chat models."
                )
        if prompt is None:
            params["messages"] = [
                {
                    "role": m["role"],
                    "content": m["content"].format(**data_instance)
                    if isinstance(m["content"], str)
                    else m["content"](data_instance),
                }
                for m in messages
            ]
        elif model in cls.chat_models:
            # convert prompt to messages
            if isinstance(prompt, str):
                prompt_msg = prompt.format(**data_instance)
            else:
                prompt_msg = prompt(data_instance)
            params["messages"] = [
                {
                    "role": "user",
                    "content": prompt_msg
                    if isinstance(prompt, str)
                    else prompt(data_instance),
                },
            ]
            params.pop("prompt", None)
        else:
            params["prompt"] = (
                prompt.format(**data_instance)
                if isinstance(prompt, str)
                else prompt(data_instance)
            )
        return params

    @classmethod
    def test(
        cls,
        data,
        config,
        eval_func=None,
        use_cache=True,
        agg_method="avg",
        return_responses_and_per_instance_result=False,
        seed=41,
        cache_path=".cache",
    ):
        """Evaluate the responses created with the config for the OpenAI API call.

        Args:
            data (list): The list of test data points.
            config (dict): Hyperparameter setting for the openai api call.
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
            seed (int): Random seed for the evaluation. Defaults to 41.
            cache_path (str): Path to the cache directory. Defaults to '.cache'.
                If a cache directory does not exist, it will be created, otherwise use the existing one.
        Returns:
            None in case of rate limit error or when a valid eval_func is not provided in either test or tune;
            Otherwise, a dict of aggregated results, responses and per instance results if `return_responses_and_per_instance_result` is True;
            Otherwise, a dict of aggregated results (responses and per instance results are not returned).
        """
        model = config["model"]
        result_agg, responses_list, result_list = {}, [], []
        metric_keys = None
        cls.set_cache(seed, cache_path)
        with diskcache.Cache(cls.cache_path) as cls._cache:
            for i, data_i in enumerate(data):
                logger.info(f"evaluating data instance {i}")
                params = cls._construct_params(data_i, config)
                response = cls._get_response(
                    params, eval_only=True, use_cache=use_cache
                )
                if response == -1:  # rate limit error, treat as invalid
                    return None
                # evaluate the quality of the responses
                responses = (
                    [r["message"]["content"].rstrip() for r in response["choices"]]
                    if model in cls.chat_models
                    else [r["text"].rstrip() for r in response["choices"]]
                )

                if eval_func is not None:
                    metrics = eval_func(responses, **data_i)
                elif hasattr(cls, "_eval_func"):
                    metrics = cls._eval_func(responses, **data_i)
                else:
                    logger.warning(
                        "Please either provide a valid eval_func or do the test after the tune function is called"
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
                assert callable(
                    metric_agg_method
                ), "please provide a callable for each metric"
                result_agg[key] = metric_agg_method([r[key] for r in result_list])
        else:
            raise ValueError(
                "agg_method needs to be a string ('avg' or 'median'),\
                or a callable, or a dictionary of callable."
            )
        # should we also return the result_list and responses_list or not?
        if return_responses_and_per_instance_result:
            return result_agg, result_list, responses_list
        else:
            return result_agg


class ChatCompletion(Completion):
    """A class for OpenAI API ChatCompletion."""

    price1K = {
        "gpt-3.5-turbo": 0.002,
        "gpt-3.5-turbo-0301": 0.002,
        "gpt-4": (0.03, 0.06),
        "gpt-4-0314": (0.03, 0.06),
        "gpt-4-32k": (0.06, 0.12),
        "gpt-4-32k-0314": (0.06, 0.12),
    }

    default_search_space = Completion.default_search_space.copy()
    default_search_space["model"] = tune.choice(["gpt-3.5-turbo", "gpt-4"])
    openai_completion_class = not ERROR and openai.ChatCompletion
