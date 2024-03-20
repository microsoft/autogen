# vLLM
[vLLM](https://github.com/vllm-project/vllm) is a locally run proxy and inference server,
providing an OpenAI-compatible API. As it performs both the proxy and the inferencing,
you don't need to install an additional inference server.

Note: vLLM does not support OpenAI's [Function Calling](https://platform.openai.com/docs/guides/function-calling)
(usable with AutoGen). However, it is in development and may be available by the time you
read this.

Running this stack requires the installation of:
1. AutoGen ([installation instructions](/docs/installation))
2. vLLM

Note: We recommend using a virtual environment for your stack, see [this article](https://microsoft.github.io/autogen/docs/installation/#create-a-virtual-environment-optional)
for guidance.

## Installing vLLM

In your terminal:

```bash
pip install vllm
```

## Choosing models

vLLM will download new models when you run the server.

The models are sourced from [Hugging Face](https://huggingface.co), a filtered list of Text
Generation models is [here](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending)
and vLLM has a list of [commonly used models](https://docs.vllm.ai/en/latest/models/supported_models.html).
Use the full model name, e.g. `mistralai/Mistral-7B-Instruct-v0.2`.

## Chat Template

vLLM uses a pre-defined chat template, unless the model has a chat template defined in its config file on Hugging Face.
This can cause an issue if the chat template doesn't allow `'role' : 'system'` messages, as used in AutoGen.

Therefore, we will create a chat template for the Mistral.AI Mistral 7B model we are using that allows roles of 'user',
'assistant', and 'system'.

Create a file name `autogenmistraltemplate.jinja` with the following content:
```` text
{{ bos_token }}
{% for message in messages %}
    {% if ((message['role'] == 'user' or message['role'] == 'system') != (loop.index0 % 2 == 0)) %}
        {{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}
    {% endif %}

    {% if (message['role'] == 'user' or message['role'] == 'system') %}
        {{ '[INST] ' + message['content'] + ' [/INST]' }}
    {% elif message['role'] == 'assistant' %}
        {{ message['content'] + eos_token}}
    {% else %}
        {{ raise_exception('Only system, user and assistant roles are supported!') }}
    {% endif %}
{% endfor %}
````

````mdx-code-block
:::warning
Chat Templates are specific to the model/model family. The example shown here is for Mistral-based models like Mistral 7B and Mixtral 8x7B.

vLLM has a number of [example templates](https://github.com/vllm-project/vllm/tree/main/examples) for models that can be a
starting point for your chat template. Just remember, the template may need to be adjusted to support 'system' role messages.
:::
````

## Running vLLM proxy server

To run vLLM with the chosen model and our chat template, in your terminal:

```bash
python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct-v0.2 --chat-template autogenmistraltemplate.jinja
```

By default, vLLM will run on 'http://0.0.0.0:8000'.

## Using vLLM with AutoGen

Now that we have the URL for the vLLM proxy server, you can use it within AutoGen in the same
way as OpenAI or cloud-based proxy servers.

As you are running this proxy server locally, no API key is required. As ```api_key``` is a mandatory
field for configurations within AutoGen we put a dummy value in it, as per the example below.

Although we are specifying the model when running the vLLM command, we must still put it into the
```model``` value for vLLM.


```python
from autogen import UserProxyAgent, ConversableAgent

local_llm_config={
    "config_list": [
        {
            "model": "mistralai/Mistral-7B-Instruct-v0.2", # Same as in vLLM command
            "api_key": "NotRequired", # Not needed
            "base_url": "http://0.0.0.0:8000/v1"  # Your vLLM URL, with '/v1' added
        }
    ],
    "cache_seed": None # Turns off caching, useful for testing different models
}

# Create the agent that uses the LLM.
assistant = ConversableAgent("agent", llm_config=local_llm_config,system_message="")

# Create the agent that represents the user in the conversation.
user_proxy = UserProxyAgent("user", code_execution_config=False,system_message="")

# Let the assistant start the conversation.  It will end when the user types exit.
assistant.initiate_chat(user_proxy, message="How can I help you today?")
```

Output:

```` text
agent (to user):

How can I help you today?

--------------------------------------------------------------------------------
Provide feedback to agent. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: Why is the sky blue?
user (to agent):

Why is the sky blue?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent (to user):


The sky appears blue due to a phenomenon called Rayleigh scattering. As sunlight reaches Earth's atmosphere, it interacts with molecules and particles in the air, causing the scattering of light. Blue light has a shorter wavelength and gets scattered more easily than other colors, which is why the sky appears blue during a clear day.

However, during sunrise and sunset, the sky can appear red, orange, or purple due to a different type of scattering called scattering by dust, pollutants, and water droplets, which scatter longer wavelengths of light more effectively.

--------------------------------------------------------------------------------
Provide feedback to agent. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: and why does it turn red?
user (to agent):

and why does it turn red?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent (to user):


During sunrise and sunset, the angle of the sun's rays in the sky is lower, and they have to pass through more of the Earth's atmosphere before reaching an observer. This additional distance results in more scattering of sunlight, which preferentially scatters the longer wavelengths (red, orange, and yellow) more than the shorter wavelengths (blue and green).

The scattering of sunlight by the Earth's atmosphere causes the red, orange, and yellow colors to be more prevalent in the sky during sunrise and sunset, resulting in the beautiful display of colors often referred to as a sunrise or sunset.

As the sun continues to set, the sky can transition to various shades of purple, pink, and eventually dark blue or black, as the available sunlight continues to decrease and the longer wavelengths are progressively scattered less effectively.

--------------------------------------------------------------------------------
Provide feedback to agent. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: exit
````
