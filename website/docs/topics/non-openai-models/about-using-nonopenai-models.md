# Non-OpenAI Models

AutoGen allows you to use non-OpenAI models through proxy servers that provide
an OpenAI-compatible API or a [custom model client](https://microsoft.github.io/autogen/blog/2024/01/26/Custom-Models)
class.

Benefits of this flexibility include access to hundreds of models, assigning specialized
models to agents (e.g., fine-tuned coding models), the ability to run AutoGen entirely
within your environment, utilising both OpenAI and non-OpenAI models in one system, and cost
reductions in inference.

## OpenAI-compatible API proxy server
Any proxy server that provides an API that is compatible with [OpenAI's API](https://platform.openai.com/docs/api-reference)
will work with AutoGen.

These proxy servers can be cloud-based or running locally within your environment.

![Cloud or Local Proxy Servers](images/cloudlocalproxy.png)

### Cloud-based proxy servers
By using cloud-based proxy servers, you are able to use models without requiring the hardware
and software to run them.

These providers can host open source/weight models, like [Hugging Face](https://huggingface.co/)
and [Mistral AI](https://mistral.ai/),
or their own closed models.

When cloud-based proxy servers provide an OpenAI-compatible API, using them in AutoGen
is straightforward. With [LLM Configuration](/docs/topics/llm_configuration) done in
the same way as when using OpenAI's models, the primary difference is typically the
authentication which is usually handled through an API key.

Examples of using cloud-based proxy servers providers that have an OpenAI-compatible API
are provided below:

- [Together AI example](/docs/topics/non-openai-models/cloud-togetherai)
- [Mistral AI example](/docs/topics/non-openai-models/cloud-mistralai)


### Locally run proxy servers
An increasing number of LLM proxy servers are available for use locally. These can be
open-source (e.g., LiteLLM, Ollama, vLLM) or closed-source (e.g., LM Studio), and are
typically used for running the full-stack within your environment.

Similar to cloud-based proxy servers, as long as these proxy servers provide an
OpenAI-compatible API, running them in AutoGen is straightforward.

Examples of using locally run proxy servers that have an OpenAI-compatible API are
provided below:

- [LiteLLM with Ollama example](/docs/topics/non-openai-models/local-litellm-ollama)
- [LM Studio](/docs/topics/non-openai-models/local-lm-studio)
- [vLLM example](/docs/topics/non-openai-models/local-vllm)

````mdx-code-block
:::tip
If you are planning to use Function Calling, not all cloud-based and local proxy servers support
Function Calling with their OpenAI-compatible API, so check their documentation.
:::
````

### Configuration for Non-OpenAI models

Whether you choose a cloud-based or locally-run proxy server, the configuration is done in
the same way as using OpenAI's models, see [LLM Configuration](/docs/topics/llm_configuration)
for further information.

You can use [model configuration filtering](/docs/topics/llm_configuration#config-list-filtering)
to assign specific models to agents.


## Custom Model Client class
For more advanced users, you can create your own custom model client class, enabling
you to define and load your own models.

See the [AutoGen with Custom Models: Empowering Users to Use Their Own Inference Mechanism](/blog/2024/01/26/Custom-Models)
blog post and [this notebook](/docs/notebooks/agentchat_custom_model/) for a guide to creating custom model client classes.
