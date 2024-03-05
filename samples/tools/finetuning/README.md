# Tools for fine-tuning the local models that power agents

This directory aims to contain tools for fine-tuning the local models that power agents.

## Fine tune a custom model client

AutoGen supports the use of custom models to power agents [see blog post here](https://microsoft.github.io/autogen/blog/2024/01/26/Custom-Models). This directory contains a tool to provide feedback to that model, that can be used to fine-tune the model.

The creator of the Custom Model Client will have to decide what kind of data is going to be fed back and how it will be used to fine-tune the model. This tool is designed to be flexible and allow for a wide variety of feedback mechanisms.

Custom Model Client will have to implement the method:

```python
def update_model(
    self, preference_data: List[Dict[str, Any]], inference_messages: List[Dict[str, Any]], **kwargs: Any
) -> Dict[str, Any]:
    """Optional method to learn from the preference data, if the model supports learning. Can be omitted.

    Learn from the preference data.

    Args:
        preference_data: The preference data.
        inference_messages: The messages used for inference.
        **kwargs: other arguments.

    Returns:
        Dict of learning stats.
    """
```

The function provided in the file `conversable_agent_update_model.py` is called by passing these arguments:

- the agent whose model is to be updated
- the preference data
- the agent who's conversation is being used to provide the inference messages

The function will call the `update_model` method of the model client and will return a dictionary containing the update stats, messages, and preference data, like so:

```python
{
    "update_stats": <the dictionary returned by the custom model client implementation>,
    "messages": <message used for inference>,
    "preference_data": <the preference data passed in when update_model was called>
}
```

An example of how to use this tool is shown below:

```python
from finetuning.conversable_agent_update_model import update_model

assistant = AssistantAgent(
    "assistant",
    system_message="You are a helpful assistant.",
    human_input_mode="NEVER",
    llm_config={
        "config_list": [<the config list containing the custom model>],
    },
)

assistant.register_model_client(model_client_cls=<TheCustomModelClientClass>)

user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
    code_execution_config=False,
    llm_config=False,
)

res = user_proxy.initiate_chat(assistant, message="the message")
response_content = res.summary

# Evaluate the summary here and provide feedback. Pretending I am going to perform DPO on the response.

# preference_data will be passed on as-is to the custom model client's update_model implementation
# so it should be in the format that the custom model client expects and is completely up to the author of the custom model client
preference_data = [("this is what the response should have been like", response_content)]

update_model_stats = update_model(assistant, preference_data, user_proxy)
```
