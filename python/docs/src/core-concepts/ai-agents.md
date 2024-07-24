# AI Agents

AGNext provides a suite of components to help developers build AI agents:

- {py:mod}`agnext.components.models` for using ChatCompletion API.
- {py:mod}`agnext.components.tools` for built-in and custom tools.
- {py:mod}`agnext.components.memory` for built-in and custom memory implementations.

This section is still under construction.
A good place to start is the [samples](https://github.com/microsoft/agnext/tree/main/python/samples).

## What is an AI Agent?

In AGNext, AI agents makes use of language models and tools to perform actions
in response to messages. Actions can be anything from generating a response
to a message, to executing code and making API calls.
AGNext does not prescribe a specific architecture for AI agents, but provides
a set of components to make it easier to build them.

In this section, we will introduce the following components: models, memory, and tools,
by incrementally build an AI agent that can respond to
messages using OpenAI's ChatCompletion API, store conversation history in memory,
and execute code snippets.

## Model Client

AGNext provides the {py:mod}`agnext.components.models` module with a suite of built-in
model clients for using ChatCompletion API.
All model clients implement the {py:class}`agnext.components.models.ChatCompletionClient` protocol class.

Let's create a simple AI agent that can respond to messages using the ChatCompletion API.

```python
import asyncio
from dataclasses import dataclass
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import ChatCompletionClient, SystemMessage, UserMessage, OpenAIChatCompletionClient
from agnext.core import CancellationToken

@dataclass
class MyMessage:
    content: str

class SimpleAgent(TypeRoutedAgent):

    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A simple agent")
        self._system_messages = [SystemMessage("You are a helpful AI assistant.")]
        self._model_client = model_client
    
    @message_handler
    async def handle_user_message(self, message: MyMessage, cancellation_token: CancellationToken) -> MyMessage:
        # Prepare input to the chat completion model.
        user_message = UserMessage(content=message.content, source="user")
        response = await self._model_client.create(self._system_messages + [user_message], cancellation_token=cancellation_token)
        # Return with the model's response.
        return MyMessage(content=response.content)
```

The `SimpleAgent` class is a subclass of the
{py:class}`agnext.components.TypeRoutedAgent` class for the convenience of automatically routing messages to the appropriate handlers.
It has a single handler, `handle_user_message`, which handles message from the user. It uses the `ChatCompletionClient` to generate a response to the message.
It then returns the response to the user, following the direct communication model.

To run the agent, we need to create a runtime and start it.

```python
async def main():
    # Create the runtime and register the agent.
    runtime = SingleThreadedAgentRuntime()
    agent = await runtime.register_and_get(
        "simple-agent",
        lambda: SimpleAgent(OpenAIChatCompletionClient(model="gpt-3.5-turbo", api_key="YOUR_API_KEY")), 
        # Leave out the api_key field if you have the API key in the environment variable OPENAI_API_KEY
    )
    # Start the runtime processing messages.
    run_context = runtime.start()
    # Send a message to the agent and get the response.
    message = MyMessage("Hello, what are some fun things to do in Seattle?")
    response = await runtime.send_message(message, agent)
    print(response)
    # Stop the runtime processing messages.
    await run_context.stop()

asyncio.run(main())
```

In the example above, we use the direct communication to send a string message
to the simple agent and get a response. A response might look like this:

```text
Hello! There are plenty of fun things to do in Seattle. Here are a few suggestions:

1. Visit the Space Needle for panoramic views of the city and surrounding areas.
2. Explore Pike Place Market, one of the oldest continually operated public farmers' markets in the United States.
3. Take a stroll through the famous Chihuly Garden and Glass exhibit showcasing the work of glass artist Dale Chihuly.
4. Enjoy a ferry ride to Bainbridge Island or explore the waterfront areas like Alki Beach.
5. Visit the Museum of Pop Culture (MoPOP) to explore exhibits on music, science fiction, and popular culture.
6. Walk around the historic neighborhoods of Pioneer Square and Capitol Hill.
7. Check out the Seattle Art Museum or the Seattle Aquarium.
8. Explore the scenic beauty of Discovery Park or the Washington Park Arboretum.

There's so much to see and do in Seattle, and these are just a few options to get you started. Let me know if you would like more specific recommendations or information on any of these suggestions!
```

## Tools

Tools are code that can be executed by an agent to perform actions. A tool
can be a simple function such as a calculator, or an API call to a third-party service
such as stock price lookup and weather forecast.
In the context of AI agents, tools are designed to be executed by agents in response to model-generated function calls.

AGNext provides the {py:mod}`agnext.components.tools` module with a suite of built-in
tools and utilities for creating and running custom tools.

### Custom Function Tools

To create a custom function tool, you just need to create a Python function
and use the {py:class}`agnext.components.tools.FunctionTool` class to wrap it.

For example, a simple tool to obtain the stock price of a company might look like this:

```python
import random
from typing_extensions import Annotated
from agnext.components.tools import FunctionTool

async def get_stock_price(ticker: str, date: Annotated[str, "Date in YYYY/MM/DD"]) -> float:
    # Returns a random stock price for demonstration purposes.
    return random.uniform(10, 200)

# Create a tool.
stock_price_tool = FunctionTool(get_stock_price, description="Get the stock price.")
```

### Tool-Equipped Agent

AGNext does not prescribe a specific way to use tools with agents, and you can
use tools in any way that makes sense for your application.
Here is an example agent class that shows one possible way to use tools with agents.

```python
import json
import asyncio
from typing import List
from dataclasses import dataclass
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler, FunctionCall
from agnext.components.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    OpenAIChatCompletionClient,
)
from agnext.components.tools import Tool, FunctionTool
from agnext.core import CancellationToken

@dataclass
class MyMessage:
    content: str

@dataclass
class FunctionExecutionException(BaseException):
    call_id: str
    content: str

class ToolAgent(TypeRoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, tools: List[Tool]) -> None:
        super().__init__("An agent with tools")
        self._system_messages = [SystemMessage("You are a helpful AI assistant.")]
        self._model_client = model_client
        self._tools = tools

    @message_handler
    async def handle_user_message(self, message: MyMessage, cancellation_token: CancellationToken) -> MyMessage:
        # Create a session of messages.
        session = [UserMessage(content=message.content, source="user")]
        # Get a response from the model.
        response = await self._model_client.create(
            self._system_messages + session, tools=self._tools, cancellation_token=cancellation_token
        )
        # Add the response to the session.
        session.append(AssistantMessage(content=response.content, source="assistant"))

        # Keep iterating until the model stops generating tool calls.
        while isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            # Execute functions called by the model by sending messages to itself.
            results: List[FunctionExecutionResult | BaseException] = await asyncio.gather(
                *[self.send_message(call, self.id) for call in response.content],
                return_exceptions=True,
            )
            # Combine the results into a single response and handle exceptions.
            function_results : List[FunctionExecutionResult] = []
            for result in results:
                if isinstance(result, FunctionExecutionResult):
                    function_results.append(result)
                elif isinstance(result, FunctionExecutionException):
                    function_results.append(FunctionExecutionResult(content=f"Error: {result}", call_id=result.call_id))
                elif isinstance(result, BaseException):
                    raise result # Unexpected exception.
            session.append(FunctionExecutionResultMessage(content=function_results))
            # Query the model again with the new response.
            response = await self._model_client.create(
                self._system_messages + session, tools=self._tools, cancellation_token=cancellation_token
            )
            session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        # Return the final response.
        return MyMessage(content=response.content)

    @message_handler
    async def handle_function_call(
        self, message: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        tool = next((tool for tool in self._tools if tool.name == message.name), None)
        if tool is None:
            raise FunctionExecutionException(call_id=message.id, content=f"Error: Tool not found: {message.name}")
        else:
            try:
                arguments = json.loads(message.arguments)
                result = await tool.run_json(args=arguments, cancellation_token=cancellation_token)
                result_as_str = tool.return_value_as_string(result)
            except json.JSONDecodeError as e:
                raise FunctionExecutionException(call_id=message.id, content=f"Error: Invalid arguments: {message.arguments}") from e
            except Exception as e:
                raise FunctionExecutionException(call_id=message.id, content=f"Error: {e}") from e
        return FunctionExecutionResult(content=result_as_str, call_id=message.id)
```

The `ToolAgent` class is much more involved than the `SimpleAgent` class, however,
the core idea can be described using a simple control flow graph:

![ToolAgent control flow graph](tool-agent-cfg.svg)

The `ToolAgent`'s `handle_my_message` handler handles messages from the user,
and determines whether the model has generated a tool call.
If the model has generated tool calls, then the handler sends a function call
message to itself to execute the tools, and then queries the model again
with the results of the tool calls.
This process continues until the model stops generating tool calls,
at which point the final response is returned to the user.

By separating the tool execution logic into a separate handler, we expose the
model-tool interactions to the agent runtime as messages, so the tool executions
can be observed externally and intercepted if necessary.

To run the agent, we need to create a runtime and register the agent.

```python
async def main() -> None:
    # Create a runtime and register the agent.
    runtime = SingleThreadedAgentRuntime()
    agent = await runtime.register_and_get(
        "tool-agent",
        lambda: ToolAgent(
            OpenAIChatCompletionClient(model="gpt-3.5-turbo", api_key="YOUR_API_KEY"),
            tools=[
                FunctionTool(get_stock_price, description="Get the stock price."),
            ],
        ),
    )
    # Start processing messages.
    run_context = runtime.start()
    # Send a direct message to the tool agent.
    response = await runtime.send_message(MyMessage("What is the stock price of NVDA on 2024/06/01?"), agent)
    print(response.content)
    # Stop processing messages.
    await run_context.stop()

asyncio.run(main())
```

In the example above, we use the direct communication to send a message to the tool agent. The agent's response might look like this:

```text
The stock price of NVDA on June 1, 2024, was $26.49.
```

See [samples](https://github.com/microsoft/agnext/tree/main/python/samples#tool-use-examples)
for more examples of using tools with agents, including how to use
broadcast communication model for tool execution, and how to intercept tool
execution for human-in-the-loop approval.

## Memory

Memory is a collection of data corresponding to the conversation history
of an agent.
Data in meory can be just a simple list of all messages,
or one which provides a view of the last N messages.
Memory can be used in agents to provide context to the model, and make sure
the context is within the limits of the model's context window.
AGNext provides the {py:mod}`agnext.components.memory` module with a suite of built-in
memory implementations.
