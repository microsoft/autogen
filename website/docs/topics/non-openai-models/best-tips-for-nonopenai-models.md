# Tips for Non-OpenAI Models

Here are some tips for using non-OpenAI Models with AutoGen.

## Finding the right model
Every model will perform differently across the operations within your AutoGen
setup, such as speaker selection, coding, function calling, content creation,
etc. On the whole, larger models (13B+) perform better with following directions
and providing more cohesive responses.

Content creation can be performed by most models.

Fine-tuned models can be great for very specific tasks, such as function calling
and coding.

Specific tasks, such as speaker selection in a Group Chat scenario, that require
very accurate outputs can be a challenge with most open source/weight models. The
use of chain-of-thought and/or few-shot prompting can help guide the LLM to provide
the output in the format you want.

## Validating your program
Testing your AutoGen setup against a very large LLM, such as OpenAI's ChatGPT or
Anthropic's Claude 3, can help validate your agent setup and configuration.

Once a setup is performing as you want, you can replace the models for your agents
with non-OpenAI models and iteratively tweak system messages, prompts, and model
selection.

## Chat template
AutoGen utilises a set of chat messages for the conversation between AutoGen/user
and LLMs. Each chat message has a role attribute that is typically `user`,
`assistant`, or `system`.

A chat template is applied during inference and some chat templates implement rules about
what roles can be used in specific sequences of messages.

For example, when using Mistral AI's API the last chat message must have a role of `user`.
In a Group Chat scenario the message used to select the next speaker will have a role of
`system` by default and the API will throw an exception for this step. To overcome this the
GroupChat's constructor has a parameter called `role_for_select_speaker_messages` that can
be used to change the role name to `user`.

```python
groupchat = autogen.GroupChat(
    agents=[user_proxy, coder, pm],
    messages=[],
    max_round=12,
    # Role for select speaker message will be set to 'user' instead of 'system'
    role_for_select_speaker_messages='user',
)
```

If the chat template associated with a model you want to use doesn't support the role
sequence and names used in AutoGen you can modify the chat template. See an example of
this on our [vLLM page](/docs/topics/non-openai-models/local-vllm#chat-template).

## Discord
Join AutoGen's [#alt-models](https://discord.com/channels/1153072414184452236/1201369716057440287)
channel on their Discord and discuss non-OpenAI models and configurations.
