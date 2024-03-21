# LiteLLM with Ollama
[LiteLLM](https://litellm.ai/) is an open-source locally run proxy server that provides an
OpenAI-compatible API. It interfaces with a large number of providers that do the inference.
To handle the inference, a popular open-source inference engine is [Ollama](https://ollama.com/).

As not all proxy servers support OpenAI's [Function Calling](https://platform.openai.com/docs/guides/function-calling) (usable with AutoGen),
LiteLLM together with Ollama enable this useful feature.

Running this stack requires the installation of:
1. AutoGen ([installation instructions](/docs/installation))
2. LiteLLM
3. Ollama

Note: We recommend using a virtual environment for your stack, see [this article](https://microsoft.github.io/autogen/docs/installation/#create-a-virtual-environment-optional) for guidance.

## Installing LiteLLM

Install LiteLLM with the proxy server functionality:

```bash
pip install litellm[proxy]
```

Note: If using Windows, run LiteLLM and Ollama within a [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install).

````mdx-code-block
:::tip
For custom LiteLLM installation instructions, see their [GitHub repository](https://github.com/BerriAI/litellm).
:::
````

## Installing Ollama

For Mac and Windows, [download Ollama](https://ollama.com/download).

For Linux:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Downloading models

Ollama has a library of models to choose from, see them [here](https://ollama.com/library).

Before you can use a model, you need to download it (using the name of the model from the library):

```bash
ollama pull llama2
```

To view the models you have downloaded and can use:

```bash
ollama list
```

````mdx-code-block
:::tip
Ollama enables the use of GGUF model files, available readily on Hugging Face. See Ollama`s [GitHub repository](https://github.com/ollama/ollama)
for examples.
:::
````

## Running LiteLLM proxy server

To run LiteLLM with the model you have downloaded, in your terminal:

```bash
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

## Using LiteLLM+Ollama with AutoGen

Now that we have the URL for the LiteLLM proxy server, you can use it within AutoGen
in the same way as OpenAI or cloud-based proxy servers.

As you are running this proxy server locally, no API key is required. Additionally, as
the model is being set when running the
LiteLLM command, no model name needs to be configured in AutoGen. However, ```model```
and ```api_key``` are mandatory fields for configurations within AutoGen so we put dummy
values in them, as per the example below.

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

## Example with Function Calling
Function calling (aka Tool calling) is a feature of OpenAI's API that AutoGen and LiteLLM support.

Below is an example of using function calling with LiteLLM and Ollama. Based on this [currency conversion](https://github.com/microsoft/autogen/blob/501f8d22726e687c55052682c20c97ce62f018ac/notebook/agentchat_function_call_currency_calculator.ipynb) notebook.

LiteLLM is loaded in the same way as the previous example, however the DolphinCoder model is used as it is better at constructing the
function calling message required.

In your terminal:

```bash
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
