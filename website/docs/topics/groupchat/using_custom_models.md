# Using Custom Models

When using `GroupChatManager` we need to pass a `GroupChat` object in the constructor, a dataclass responsible for
gathering agents, preparing messages from prompt templates and selecting speakers
(eventually using `speaker_selection_method` as described [here](customized_speaker_selection)).

To do so GroupChat internally initializes two instances of ConversableAgent.
In order to control the model clients used by the agents instantiated within the GroupChat, which already receives the
`llm_config` passed to GroupChatManager, the optional `model_client_cls` attribute can be set.


## Example
First we need to define an `llm_config` and define some agents that will partake in the group chat:
```python
from autogen import GroupChat, ConversableAgent, GroupChatManager, UserProxyAgent
from somewhere import MyModelClient


# Define the custom model configuration
llm_config = {
    "config_list": [
        {
            "model": "gpt-3.5-turbo",
            "model_client_cls": "MyModelClient"
        }
    ]
}

# Initialize the agents with the custom model
agent1 = ConversableAgent(
    name="Agent 1",
    llm_config=llm_config
)
agent1.register_model_client(model_client_cls=MyModelClient)

agent2 = ConversableAgent(
    name="Agent 2",
    llm_config=llm_config
)
agent2.register_model_client(model_client_cls=MyModelClient)

agent3 = ConversableAgent(
    name="Agent 2",
    llm_config=llm_config
)
agent3.register_model_client(model_client_cls=MyModelClient)

user_proxy = UserProxyAgent(name="user", llm_config=llm_config, code_execution_config={"use_docker": False})
user_proxy.register_model_client(MyModelClient)
```

Note that the agents definition illustrated here is minimal and might not suit your needs. The only aim is to show a
basic setup for a group chat scenario.

We then create a `GroupChat` and, if we want the underlying agents used by GroupChat to use our
custom client, we will pass it in the `model_client_cls` attribute.

Finally we create an instance of `GroupChatManager` and pass the config to it. This same config will be forwarded to
the GroupChat, that (if needed) will automatically handle registration of custom models only.

```python
# Create a GroupChat instance and add the agents
group_chat = GroupChat(agents=[agent1, agent2, agent3], messages=[], model_client_cls=MyModelClient)

# Create the GroupChatManager with the GroupChat, UserProxy, and model configuration
chat_manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
chat_manager.register_model_client(model_client_cls=MyModelClient)

# Initiate the chat using the UserProxy
user_proxy.initiate_chat(chat_manager, initial_message="Suggest me the most trending papers in microbiology that you think might interest me")

```

This attribute can either be a class or a list of classes which adheres to the `ModelClient` protocol (see
[this link](../non-openai-models/about-using-nonopenai-models) for more info about defining a custom model client
class).

Note that it is not necessary to define a `model_client_cls` when working with Azure OpenAI, OpenAI or other non-custom
models natively supported by the library.
