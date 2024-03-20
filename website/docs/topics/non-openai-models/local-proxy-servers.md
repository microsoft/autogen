# Locally Run Proxy Servers
LLM proxy servers allow you to run models within your environment and provide an OpenAI-compatible
API for your applications to use, including AutoGen.

These proxy servers can be open-source or closed-source.

## LiteLLM with Ollama
[LiteLLM](https://litellm.ai/) is a proxy server, providing an OpenAI-compatible API, and it interfaces with
a large number of providers that do the inference. To handle the inference, a popular open-source inference engine is [Ollama](https://ollama.com/).

As not all proxy servers support OpenAI's [Function Calling](https://platform.openai.com/docs/guides/function-calling) (usable with AutoGen), LiteLLM together with Ollama enable this useful feature.

Running this stack requires the installation of:
1. AutoGen ([installation instructions](/docs/installation))
2. LiteLLM
3. Ollama

Note: We recommend using a virtual environment for your stack, see [this article](https://microsoft.github.io/autogen/docs/installation/#create-a-virtual-environment-optional) for guidance.

### Installing LiteLLM

Install LiteLLM with the proxy functionality:

```python
pip install litellm[proxy]
```

Note: If using Windows, run LiteLLM and Ollama within a [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install).

````mdx-code-block
:::tip
For custom LiteLLM installation instructions, see their [GitHub repository](https://github.com/BerriAI/litellm).
:::
````

### Installing Ollama

For Mac and Windows, [download Ollama](https://ollama.com/download).

For Linux:

```python
curl -fsSL https://ollama.com/install.sh | sh
```

### Downloading models

Ollama has a library of models to choose from, see them [here](https://ollama.com/library).

Before you can use a model, you need to download it (using the name of the model from the library):

```python
ollama pull llama2
```

To view the models you have downloaded and can use:

```python
ollama list
```

````mdx-code-block
:::tip
Ollama enables the use of GGUF model files, available readily on Hugging Face. See Ollama`s [Github repository](https://github.com/ollama/ollama) for examples. 
:::
````

### Running LiteLLM proxy server

To run LiteLLM with the model you have downloaded, in your terminal:

```python
litellm --model ollama_chat/llama2
```

```` text
INFO:     Started server process [19040]
INFO:     Waiting for application startup.

#------------------------------------------------------------#
#                                                            #
#       'This feature doesn't meet my needs because...'       #
#        https://github.com/BerriAI/litellm/issues/new        #
#                                                            #
#------------------------------------------------------------#

 Thank you for using LiteLLM! - Krrish & Ishaan



Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new


INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
````

This will run the proxy server and it will be available at 'http://0.0.0.0:4000/'.

### Using LiteLLM+Ollama with AutoGen

Now that we have the URL for the LiteLLM proxy server, you can use it within AutoGen in the same way as OpenAI or Cloud-based proxy servers.

As you are running this proxy server locally, no API key is required. Additionally, as the model is being set when running the
LiteLLM command, no model name needs to be configured in AutoGen. However, ```model``` and ```api_key``` are mandatory fields for configurations within AutoGen so we put dummy values in them, as per the example below.

```python
from autogen import UserProxyAgent, ConversableAgent

local_llm_config={
    "config_list": [
        {
            "model": "NotRequired", # Loaded with LiteLLM command
            "api_key": "NotRequired", # Not needed
            "base_url": "http://0.0.0.0:4000"  # Your LiteLLM URL
        }
    ],
    "cache_seed": None # Turns off caching, useful for testing different models
}

# Create the agent that uses the LLM.
assistant = ConversableAgent("agent", llm_config=local_llm_config)

# Create the agent that represents the user in the conversation.
user_proxy = UserProxyAgent("user", code_execution_config=False)

# Let the assistant start the conversation.  It will end when the user types exit.
assistant.initiate_chat(user_proxy, message="How can I help you today?")
```

Output:

```` text
agent (to user):

How can I help you today?

--------------------------------------------------------------------------------
Provide feedback to agent. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: Tell me, why is the sky blue?
user (to agent):

Tell me, why is the sky blue?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent (to user):

Ah, a classic question! The sky appears blue because of a phenomenon called Rayleigh scattering. When sunlight enters Earth's atmosphere, it encounters tiny molecules of gases such as nitrogen and oxygen. These molecules scatter the light in all directions, but they scatter shorter (blue) wavelengths more than longer (red) wavelengths. This is why the sky looks blue during the daytime, especially in the direction of the sun.

But wait, there's more! The color of the sky can also change depending on the time of day and atmospheric conditions. For example, during sunrise and sunset, the sky can take on hues of red, orange, and pink due to the way that light interacts with the Earth's atmosphere. And if you're in a location with a lot of dust or pollution, the sky may appear more hazy or gray.

So there you have it! The sky is blue because of the way that light interacts with the Earth's atmosphere, and there are many factors that can affect its appearance. Is there anything else you'd like to know?

--------------------------------------------------------------------------------
Provide feedback to agent. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: And what would it take to make it red?
user (to agent):

And what would it take to make it red?

--------------------------------------------------------------------------------

>>>>>>>> USING AUTO REPLY...
agent (to user):

Ah, an interesting question! To make the sky appear red, we need to look at the scattering of light in a different way. When the sun is low on the horizon, the light it emits has to travel through a longer distance in the atmosphere to reach our eyes. As a result, much of the shorter wavelength blue light is scattered away, leaving mainly the longer wavelength red and orange light to reach our eyes. This is why the sky can take on hues of red, orange, and pink during sunrise and sunset.

However, if we were to somehow change the composition of the atmosphere or add some additional particles into the air, we could potentially make the sky appear red even when the sun is high in the sky. For example, if we were to add a lot of dust or smoke into the atmosphere, the sky might take on a reddish hue due to the scattering of light by these particles. Or, if we were to create a situation where the air was filled with a high concentration of certain gases, such as nitrogen oxides or sulfur compounds, the sky could potentially appear red or orange as a result of the way that these gases interact with light.

So there you have it! While the sky is typically blue during the daytime due to Rayleigh scattering, there are many other factors that can affect its appearance, and with the right conditions, we can even make the sky appear red! Is there anything else you'd like to know?

--------------------------------------------------------------------------------
Provide feedback to agent. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: exit
````

### Example with Function Calling
Function calling (aka Tool calling) is a feature of OpenAI's API that AutoGen and LiteLLM support.

Below is an example of using function calling with LiteLLM and Ollama. Based on this [currency conversion](https://github.com/microsoft/autogen/blob/501f8d22726e687c55052682c20c97ce62f018ac/notebook/agentchat_function_call_currency_calculator.ipynb) notebook.

LiteLLM is loaded in the same way as the previous example, however the DolphinCoder model is used as it is better at constructing the
function calling message required.

In your terminal:

```python
litellm --model ollama_chat/dolphincoder
```


```python
import autogen
from typing import Literal
from typing_extensions import Annotated

local_llm_config={
    "config_list": [
        {
            "model": "NotRequired", # Loaded with LiteLLM command
            "api_key": "NotRequired", # Not needed
            "base_url": "http://0.0.0.0:4000"  # Your LiteLLM URL
        }
    ],
    "cache_seed": None # Turns off caching, useful for testing different models
}

# Create the agent and include examples of the function calling JSON in the prompt
# to help guide the model
chatbot = autogen.AssistantAgent(
    name="chatbot",
    system_message="""For currency exchange tasks, 
        only use the functions you have been provided with. 
        Output 'TERMINATE' when an answer has been provided. 
        Do not include the function name or result in the JSON.
        Example of the return JSON is: 
        {
            "parameter_1_name": 100.00,
            "parameter_2_name": "ABC",
            "parameter_3_name": "DEF",
        }. 
        Another example of the return JSON is: 
        {
            "parameter_1_name": "GHI",
            "parameter_2_name": "ABC",
            "parameter_3_name": "DEF",
            "parameter_4_name": 123.00,
        }. """,

    llm_config=local_llm_config,
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x.get("content", ""),
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
)


CurrencySymbol = Literal["USD", "EUR"]

# Define our function that we expect to call
def exchange_rate(base_currency: CurrencySymbol, quote_currency: CurrencySymbol) -> float:
    if base_currency == quote_currency:
        return 1.0
    elif base_currency == "USD" and quote_currency == "EUR":
        return 1 / 1.1
    elif base_currency == "EUR" and quote_currency == "USD":
        return 1.1
    else:
        raise ValueError(f"Unknown currencies {base_currency}, {quote_currency}")

# Register the function with the agent
@user_proxy.register_for_execution()
@chatbot.register_for_llm(description="Currency exchange calculator.")
def currency_calculator(
    base_amount: Annotated[float, "Amount of currency in base_currency"],
    base_currency: Annotated[CurrencySymbol, "Base currency"] = "USD",
    quote_currency: Annotated[CurrencySymbol, "Quote currency"] = "EUR",
) -> str:
    quote_amount = exchange_rate(base_currency, quote_currency) * base_amount
    return f"{format(quote_amount, '.2f')} {quote_currency}"

# start the conversation
res = user_proxy.initiate_chat(
    chatbot,
    message="How much is 123.45 EUR in USD?",
    summary_method="reflection_with_llm",
)
```

Output:

```` text
user_proxy (to chatbot):

How much is 123.45 EUR in USD?

--------------------------------------------------------------------------------
chatbot (to user_proxy):

***** Suggested tool Call (call_c93c4390-93d5-4a28-b40d-09fe74cc58da): currency_calculator *****
Arguments: 
{
  "base_amount": 123.45,
  "base_currency": "EUR",
  "quote_currency": "USD"
}


************************************************************************************************

--------------------------------------------------------------------------------

>>>>>>>> EXECUTING FUNCTION currency_calculator...
user_proxy (to chatbot):

user_proxy (to chatbot):

***** Response from calling tool "call_c93c4390-93d5-4a28-b40d-09fe74cc58da" *****
135.80 USD
**********************************************************************************

--------------------------------------------------------------------------------
chatbot (to user_proxy):

***** Suggested tool Call (call_d8fd94de-5286-4ef6-b1f6-72c826531ff9): currency_calculator *****
Arguments: 
{
  "base_amount": 123.45,
  "base_currency": "EUR",
  "quote_currency": "USD"
}


************************************************************************************************
````

````mdx-code-block
:::warning
Not all open source/weight models are suitable for function calling and AutoGen continues to be
developed to provide wider support for open source models.

The [#alt-models](https://discord.com/channels/1153072414184452236/1201369716057440287) channel
on AutoGen's Discord is an active community discussing the use of open source/weight models
with AutoGen.
:::
````

## vLLM
[vLLM](https://github.com/vllm-project/vllm) is a proxy and inference server, providing an
OpenAI-compatible API. As it performs both the proxy and the inferencing, you don't need to
install an additional inference server.

Note: vLLM does not support OpenAI's [Function Calling](https://platform.openai.com/docs/guides/function-calling)
(usable with AutoGen). However, it is in development and may be available by the time you read this.

Running this stack requires the installation of:
1. AutoGen ([installation instructions](/docs/installation))
2. vLLM

Note: We recommend using a virtual environment for your stack, see [this article](https://microsoft.github.io/autogen/docs/installation/#create-a-virtual-environment-optional)
for guidance.

### Installing vLLM

In your terminal:

```python
pip install vllm
```

### Choosing models

vLLM will download new models when you run the server.

The models are sourced from [Hugging Face](huggingface.co), a filtered list of Text
Generation models is [here](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending)
and vLLM has a list of [commonly used models](https://docs.vllm.ai/en/latest/models/supported_models.html).
Use the full model name, e.g. `mistralai/Mistral-7B-Instruct-v0.2`.

### Chat Template

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

### Running vLLM proxy server

To run vLLM with the chosen model and our chat template, in your terminal:

```python
python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct-v0.2 --chat-template autogenmistraltemplate.jinja
```

By default, vLLM will run on 'http://0.0.0.0:8000'.

### Using vLLM with AutoGen

Now that we have the URL for the vLLM proxy server, you can use it within AutoGen in the same
way as OpenAI or Cloud-based proxy servers.

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

````mdx-code-block
:::tip
If you are planning to use Function Calling, not all local proxy servers support Function Calling with their OpenAI-compatible API, so check their documentation.
:::
````