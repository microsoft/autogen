# Introduction to Transform Messages

Why do we need to handle long contexts? The problem arises from several constraints and requirements:

1. Token limits: LLMs have token limits that restrict the amount of textual data they can process. If we exceed these limits, we may encounter errors or incur additional costs. By preprocessing the chat history, we can ensure that we stay within the acceptable token range.

2. Context relevance: As conversations progress, retaining the entire chat history may become less relevant or even counterproductive. Keeping only the most recent and pertinent messages can help the LLMs focus on the most crucial context, leading to more accurate and relevant responses.

3. Efficiency: Processing long contexts can consume more computational resources, leading to slower response times.

## Transform Messages Capability

The `TransformMessages` capability is designed to modify incoming messages before they are processed by the LLM agent. This can include limiting the number of messages, truncating messages to meet token limits, and more.

:::info Requirements
Install `autogen-agentchat`:

```bash
pip install autogen-agentchat~=0.2
```

For more information, please refer to the [installation guide](/docs/installation/).
:::

### Exploring and Understanding Transformations

Let's start by exploring the available transformations and understanding how they work. We will start off by importing the required modules.

```python
import copy
import pprint

from autogen.agentchat.contrib.capabilities import transforms
```

#### Example 1: Limiting the Total Number of Messages

Consider a scenario where you want to limit the context history to only the most recent messages to maintain efficiency and relevance. You can achieve this with the MessageHistoryLimiter transformation:

```python
# Limit the message history to the 3 most recent messages
max_msg_transfrom = transforms.MessageHistoryLimiter(max_messages=3)

messages = [
    {"role": "user", "content": "hello"},
    {"role": "assistant", "content": [{"type": "text", "text": "there"}]},
    {"role": "user", "content": "how"},
    {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
    {"role": "user", "content": "very very very very very very long string"},
]

processed_messages = max_msg_transfrom.apply_transform(copy.deepcopy(messages))
pprint.pprint(processed_messages)
```

```console
[{'content': 'how', 'role': 'user'},
{'content': [{'text': 'are you doing?', 'type': 'text'}], 'role': 'assistant'},
{'content': 'very very very very very very long string', 'role': 'user'}]
```

By applying the `MessageHistoryLimiter`, we can see that we were able to limit the context history to the 3 most recent messages. However, if the splitting point is between a "tool_calls" and "tool" pair, the complete pair will be included to obey the OpenAI API call constraints.

```python
max_msg_transfrom = transforms.MessageHistoryLimiter(max_messages=3)

messages = [
    {"role": "user", "content": "hello"},
    {"role": "tool_calls", "content": "calling_tool"},
    {"role": "tool", "content": "tool_response"},
    {"role": "user", "content": "how are you"},
    {"role": "assistant", "content": [{"type": "text", "text": "are you doing?"}]},
]

processed_messages = max_msg_transfrom.apply_transform(copy.deepcopy(messages))
pprint.pprint(processed_messages)
```
```console
[{'content': 'calling_tool', 'role': 'tool_calls'},
{'content': 'tool_response', 'role': 'tool'},
{'content': 'how are you', 'role': 'user'},
{'content': [{'text': 'are you doing?', 'type': 'text'}], 'role': 'assistant'}]
```

#### Example 2: Limiting the Number of Tokens

To adhere to token limitations, use the `MessageTokenLimiter` transformation. This limits tokens per message and the total token count across all messages. Additionally, a `min_tokens` threshold can be applied:

```python
# Limit the token limit per message to 3 tokens
token_limit_transform = transforms.MessageTokenLimiter(max_tokens_per_message=3, min_tokens=10)

processed_messages = token_limit_transform.apply_transform(copy.deepcopy(messages))

pprint.pprint(processed_messages)
```

```console
[{'content': 'hello', 'role': 'user'},
{'content': [{'text': 'there', 'type': 'text'}], 'role': 'assistant'},
{'content': 'how', 'role': 'user'},
{'content': [{'text': 'are you doing', 'type': 'text'}], 'role': 'assistant'},
{'content': 'very very very', 'role': 'user'}]
```

We can see that we were able to limit the number of tokens to 3, which is equivalent to 3 words for this instance.

In the following example we will explore the effect of the `min_tokens` threshold.

```python
short_messages = [
    {"role": "user", "content": "hello there, how are you?"},
    {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
]

processed_short_messages = token_limit_transform.apply_transform(copy.deepcopy(short_messages))

pprint.pprint(processed_short_messages)
```

```console
[{'content': 'hello there, how are you?', 'role': 'user'},
 {'content': [{'text': 'hello', 'type': 'text'}], 'role': 'assistant'}]
```

We can see that no transformation was applied, because the threshold of 10 total tokens was not reached.

### Apply Transformations Using Agents

So far, we have only tested the `MessageHistoryLimiter` and `MessageTokenLimiter` transformations individually, let's test these transformations with AutoGen's agents.

#### Setting Up the Stage

```python
import os
import copy

import autogen
from autogen.agentchat.contrib.capabilities import transform_messages, transforms
from typing import Dict, List

config_list = [{"model": "gpt-3.5-turbo", "api_key": os.getenv("OPENAI_API_KEY")}]

# Define your agent; the user proxy and an assistant
assistant = autogen.AssistantAgent(
    "assistant",
    llm_config={"config_list": config_list},
)
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
    max_consecutive_auto_reply=10,
)
```

:::tip
Learn more about configuring LLMs for agents [here](/docs/topics/llm_configuration).
:::

We first need to write the `test` function that creates a very long chat history by exchanging messages between an assistant and a user proxy agent, and then attempts to initiate a new chat without clearing the history, potentially triggering an error due to token limits.

```python
# Create a very long chat history that is bound to cause a crash for gpt 3.5
def test(assistant: autogen.ConversableAgent, user_proxy: autogen.UserProxyAgent):
    for _ in range(1000):
        # define a fake, very long messages
        assitant_msg = {"role": "assistant", "content": "test " * 1000}
        user_msg = {"role": "user", "content": ""}

        assistant.send(assitant_msg, user_proxy, request_reply=False, silent=True)
        user_proxy.send(user_msg, assistant, request_reply=False, silent=True)

    try:
        user_proxy.initiate_chat(assistant, message="plot and save a graph of x^2 from -10 to 10", clear_history=False)
    except Exception as e:
        print(f"Encountered an error with the base assistant: \n{e}")
```

The first run will be the default implementation, where the agent does not have the `TransformMessages` capability.

```python
test(assistant, user_proxy)
```

Running this test will result in an error due to the large number of tokens sent to OpenAI's gpt 3.5.

```console
user_proxy (to assistant):

plot and save a graph of x^2 from -10 to 10

--------------------------------------------------------------------------------
Encountered an error with the base assistant
Error code: 429 - {'error': {'message': 'Request too large for gpt-3.5-turbo in organization org-U58JZBsXUVAJPlx2MtPYmdx1 on tokens per min (TPM): Limit 60000, Requested 1252546. The input or output tokens must be reduced in order to run successfully. Visit https://platform.openai.com/account/rate-limits to learn more.', 'type': 'tokens', 'param': None, 'code': 'rate_limit_exceeded'}}
```

Now let's add the `TransformMessages` capability to the assistant and run the same test.

```python
context_handling = transform_messages.TransformMessages(
    transforms=[
        transforms.MessageHistoryLimiter(max_messages=10),
        transforms.MessageTokenLimiter(max_tokens=1000, max_tokens_per_message=50, min_tokens=500),
    ]
)
context_handling.add_to_agent(assistant)

test(assistant, user_proxy)
```

The following console output shows that the agent is now able to handle the large number of tokens sent to OpenAI's gpt 3.5.

`````console
user_proxy (to assistant):

plot and save a graph of x^2 from -10 to 10

--------------------------------------------------------------------------------
Truncated 3804 tokens. Tokens reduced from 4019 to 215
assistant (to user_proxy):

To plot and save a graph of \( x^2 \) from -10 to 10, we can use Python with the matplotlib library. Here's the code to generate the plot and save it to a file named "plot.png":

```python
# filename: plot_quadratic.py
import matplotlib.pyplot as plt
import numpy as np

# Create an array of x values from -10 to 10
x = np.linspace(-10, 10, 100)
y = x**2

# Plot the graph
plt.plot(x, y)
plt.xlabel('x')
plt.ylabel('x^2')
plt.title('Plot of x^2')
plt.grid(True)

# Save the plot as an image file
plt.savefig('plot.png')

# Display the plot
plt.show()
````

You can run this script in a Python environment. It will generate a plot of \( x^2 \) from -10 to 10 and save it as "plot.png" in the same directory where the script is executed.

Execute the Python script to create and save the graph.
After executing the code, you should see a file named "plot.png" in the current directory, containing the graph of \( x^2 \) from -10 to 10. You can view this file to see the plotted graph.

Is there anything else you would like to do or need help with?
If not, you can type "TERMINATE" to end our conversation.

---

`````

### Create Custom Transformations to Handle Sensitive Content

You can create custom transformations by implementing the `MessageTransform` protocol, which provides flexibility to handle various use cases. One practical application is to create a custom transformation that redacts sensitive information, such as API keys, passwords, or personal data, from the chat history or logs. This ensures that confidential data is not inadvertently exposed, enhancing the security and privacy of your conversational AI system.

We will demonstrate this by implementing a custom transformation called `MessageRedact` that detects and redacts OpenAI API keys from the conversation history. This transformation is particularly useful when you want to prevent accidental leaks of API keys, which could compromise the security of your system.

```python
import os
import pprint
import copy
import re

import autogen
from autogen.agentchat.contrib.capabilities import transform_messages, transforms
from typing import Dict, List

# The transform must adhere to transform_messages.MessageTransform protocol.
class MessageRedact:
    def __init__(self):
        self._openai_key_pattern = r"sk-([a-zA-Z0-9]{48})"
        self._replacement_string = "REDACTED"

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        temp_messages = copy.deepcopy(messages)

        for message in temp_messages:
            if isinstance(message["content"], str):
                message["content"] = re.sub(self._openai_key_pattern, self._replacement_string, message["content"])
            elif isinstance(message["content"], list):
                for item in message["content"]:
                    if item["type"] == "text":
                        item["text"] = re.sub(self._openai_key_pattern, self._replacement_string, item["text"])
        return temp_messages

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        keys_redacted = self._count_redacted(post_transform_messages) - self._count_redacted(pre_transform_messages)
        if keys_redacted > 0:
            return f"Redacted {keys_redacted} OpenAI API keys.", True
        return "", False

    def _count_redacted(self, messages: List[Dict]) -> int:
        # counts occurrences of "REDACTED" in message content
        count = 0
        for message in messages:
            if isinstance(message["content"], str):
                if "REDACTED" in message["content"]:
                    count += 1
            elif isinstance(message["content"], list):
                for item in message["content"]:
                    if isinstance(item, dict) and "text" in item:
                        if "REDACTED" in item["text"]:
                            count += 1
        return count


assistant_with_redact = autogen.AssistantAgent(
    "assistant",
    llm_config=llm_config,
    max_consecutive_auto_reply=1,
)
redact_handling = transform_messages.TransformMessages(transforms=[MessageRedact()])

redact_handling.add_to_agent(assistant_with_redact)

user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
)

messages = [
    {"content": "api key 1 = sk-7nwt00xv6fuegfu3gnwmhrgxvuc1cyrhxcq1quur9zvf05fy"},  # Don't worry, the key is randomly generated
    {"content": [{"type": "text", "text": "API key 2 = sk-9wi0gf1j2rz6utaqd3ww3o6c1h1n28wviypk7bd81wlj95an"}]},
]

for message in messages:
    user_proxy.send(message, assistant_with_redact, request_reply=False, silent=True)

result = user_proxy.initiate_chat(
    assistant_with_redact, message="What are the two API keys that I just provided", clear_history=False

```

```console
user_proxy (to assistant):

What are the two API keys that I just provided

--------------------------------------------------------------------------------
Redacted 2 OpenAI API keys.
assistant (to user_proxy):

As an AI, I must inform you that it is not safe to share API keys publicly as they can be used to access your private data or services that can incur costs. Given that you've typed "REDACTED" instead of the actual keys, it seems you are aware of the privacy concerns and are likely testing my response or simulating an exchange without exposing real credentials, which is a good practice for privacy and security reasons.

To respond directly to your direct question: The two API keys you provided are both placeholders indicated by the text "REDACTED", and not actual API keys. If these were real keys, I would have reiterated the importance of keeping them secure and would not display them here.

Remember to keep your actual API keys confidential to prevent unauthorized use. If you've accidentally exposed real API keys, you should revoke or regenerate them as soon as possible through the corresponding service's API management console.

--------------------------------------------------------------------------------
user_proxy (to assistant):



--------------------------------------------------------------------------------
Redacted 2 OpenAI API keys.
```
