This tutorial shows how to use tools in an agent.

## What is tool
Tools are pre-defined functions in user's project that agent can invoke. Agent can use tools to perform actions like search web, perform calculations, etc. With tools, it can greatly extend the capabilities of an agent.

> [!NOTE]
> To use tools with agent, the backend LLM model used by the agent needs to support tool calling. Here are some of the LLM models that support tool calling as of 06/21/2024
> - GPT-3.5-turbo with version >= 0613
> - GPT-4 series
> - Gemini series
> - OPEN_MISTRAL_7B
> - ...
>
> This tutorial uses the latest `GPT-3.5-turbo` as example.

> [!NOTE]
> The complete code example can be found in [Use_Tools_With_Agent.cs](https://github.com/microsoft/autogen/blob/main/dotnet/sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs)

## Key Concepts
- @AutoGen.Core.FunctionContract: The contract of a function that agent can invoke. It contains the function name, description, parameters schema, and return type.
- @AutoGen.Core.ToolCallMessage: A message type that represents a tool call request in AutoGen.Net.
- @AutoGen.Core.ToolCallResultMessage: A message type that represents a tool call result in AutoGen.Net.
- @AutoGen.Core.ToolCallAggregateMessage: An aggregate message type that represents a tool call request and its result in a single message in AutoGen.Net.
- @AutoGen.Core.FunctionCallMiddleware: A middleware that pass the @AutoGen.Core.FunctionContract to the agent when generating response, and process the tool call response when receiving a @AutoGen.Core.ToolCallMessage.

> [!Tip]
> You can Use AutoGen.SourceGenerator to automatically generate type-safe @AutoGen.Core.FunctionContract instead of manually defining them. For more information, please check out [Create type-safe function](../articles/Create-type-safe-function-call.md).

## Install AutoGen and AutoGen.SourceGenerator
First, install the AutoGen and AutoGen.SourceGenerator package using the following command:

```bash
dotnet add package AutoGen
dotnet add package AutoGen.SourceGenerator
```

Also, you might need to enable structural xml document support by setting `GenerateDocumentationFile` property to true in your project file. This allows source generator to leverage the documentation of the function when generating the function definition.

```xml
<PropertyGroup>
    <!-- This enables structural xml document support -->
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
</PropertyGroup>
```

## Add Using Statements

[!code-csharp[Using Statements](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Using)]

## Create agent

Create an @AutoGen.OpenAI.OpenAIChatAgent with `GPT-3.5-turbo` as the backend LLM model.

[!code-csharp[Create an agent with tools](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Create_Agent)]

## Define `Tool` class and create tools
Create a `public partial` class to host the tools you want to use in AutoGen agents. The method has to be a `public` instance method and its return type must be `Task<string>`. After the methods is defined, mark them with @AutoGen.Core.FunctionAttribute attribute.

In the following example, we define a `GetWeather` tool that returns the weather information of a city.

[!code-csharp[Define Tool class](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Tools)]
[!code-csharp[Create tools](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Create_tools)]

## Tool call without auto-invoke
In this case, when receiving a @AutoGen.Core.ToolCallMessage, the agent will not automatically invoke the tool. Instead, the agent will return the original message back to the user. The user can then decide whether to invoke the tool or not.

![single-turn tool call without auto-invoke](../images/articles/CreateAgentWithTools/single-turn-tool-call-without-auto-invoke.png)

To implement this, you can create the @AutoGen.Core.FunctionCallMiddleware without passing the `functionMap` parameter to the constructor so that the middleware will not automatically invoke the tool once it receives a @AutoGen.Core.ToolCallMessage from its inner agent.

[!code-csharp[Single-turn tool call without auto-invoke](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Create_no_invoke_middleware)]

After creating the function call middleware, you can register it to the agent using `RegisterMiddleware` method, which will return a new agent which can use the methods defined in the `Tool` class.

[!code-csharp[Generate Response](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Single_Turn_No_Invoke)]

## Tool call with auto-invoke
In this case, the agent will automatically invoke the tool when receiving a @AutoGen.Core.ToolCallMessage and return the @AutoGen.Core.ToolCallAggregateMessage which contains both the tool call request and the tool call result.

![single-turn tool call with auto-invoke](../images/articles/CreateAgentWithTools/single-turn-tool-call-with-auto-invoke.png)

To implement this, you can create the @AutoGen.Core.FunctionCallMiddleware with the `functionMap` parameter so that the middleware will automatically invoke the tool once it receives a @AutoGen.Core.ToolCallMessage from its inner agent.

[!code-csharp[Single-turn tool call with auto-invoke](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Create_auto_invoke_middleware)]

After creating the function call middleware, you can register it to the agent using `RegisterMiddleware` method, which will return a new agent which can use the methods defined in the `Tool` class.

[!code-csharp[Generate Response](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Single_Turn_Auto_Invoke)]

## Send the tool call result back to LLM to generate further response
In some cases, you may want to send the tool call result back to the LLM to generate further response. To do this, you can send the tool call response from agent back to the LLM by calling the `SendAsync` method of the agent.

[!code-csharp[Generate Response](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=Multi_Turn_Tool_Call)]

## Parallel tool call
Some LLM models support parallel tool call, which returns multiple tool calls in one single message. Note that @AutoGen.Core.FunctionCallMiddleware has already handled the parallel tool call for you. When it receives a @AutoGen.Core.ToolCallMessage that contains multiple tool calls, it will automatically invoke all the tools in the sequantial order and return the @AutoGen.Core.ToolCallAggregateMessage which contains all the tool call requests and results.

[!code-csharp[Generate Response](../../sample/AutoGen.BasicSamples/GettingStart/Use_Tools_With_Agent.cs?name=parallel_tool_call)]

## Further Reading
- [Function-call-with-openai](../articles/OpenAIChatAgent-use-function-call.md)
- [Function-call-with-gemini](../articles/AutoGen.Gemini/Function-call-with-gemini.md)
- [Use kernel plugin in other agents](../articles/AutoGen.SemanticKernel/Use-kernel-plugin-in-other-agents.md)
- [function call in mistral](../articles/MistralChatAgent-use-function-call.md)