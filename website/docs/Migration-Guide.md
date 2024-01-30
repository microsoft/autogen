# Migration Guide

## Migrating to 0.2

openai v1 is a total rewrite of the library with many breaking changes. For example, the inference requires instantiating a client, instead of using a global class method.
Therefore, some changes are required for users of `pyautogen<0.2`.

- `api_base` -> `base_url`, `request_timeout` -> `timeout` in `llm_config` and `config_list`. `max_retry_period` and `retry_wait_time` are deprecated. `max_retries` can be set for each client.
- MathChat is unsupported until it is tested in future release.
- `autogen.Completion` and `autogen.ChatCompletion` are deprecated. The essential functionalities are moved to `autogen.OpenAIWrapper`:

```python
from autogen import OpenAIWrapper
client = OpenAIWrapper(config_list=config_list)
response = client.create(messages=[{"role": "user", "content": "2+2="}])
print(client.extract_text_or_completion_object(response))
```

- Inference parameter tuning and inference logging features are currently unavailable in `OpenAIWrapper`. Logging will be added in a future release.
Inference parameter tuning can be done via [`flaml.tune`](https://microsoft.github.io/FLAML/docs/Use-Cases/Tune-User-Defined-Function).
- `seed` in autogen is renamed into `cache_seed` to accommodate the newly added `seed` param in openai chat completion api. `use_cache` is removed as a kwarg in `OpenAIWrapper.create()` for being automatically decided by `cache_seed`: int | None. The difference between autogen's `cache_seed` and openai's `seed` is that:
  - autogen uses local disk cache to guarantee the exactly same output is produced for the same input and when cache is hit, no openai api call will be made.
  - openai's `seed` is a best-effort deterministic sampling with no guarantee of determinism. When using openai's `seed` with `cache_seed` set to None, even for the same input, an openai api call will be made and there is no guarantee for getting exactly the same output.
