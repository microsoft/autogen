In semantic kernel, a kernel plugin is a collection of kernel functions that can be invoked during LLM calls. Semantic kernel provides a list of built-in plugins, like [core plugins](https://github.com/microsoft/semantic-kernel/tree/main/dotnet/src/Plugins/Plugins.Core), [web search plugin](https://github.com/microsoft/semantic-kernel/tree/main/dotnet/src/Plugins/Plugins.Web) and many more. You can also create your own plugins and use them in semantic kernel. Kernel plugins greatly extend the capabilities of semantic kernel and can be used to perform various tasks like web search, image search, text summarization, etc.

`AutoGen.SemanticKernel` provides a middleware called @AutoGen.SemanticKernel.KernelPluginMiddleware that allows you to use semantic kernel plugins in other AutoGen agents like @AutoGen.OpenAI.OpenAIChatAgent. The following example shows how to define a simple plugin with a single `GetWeather` function and use it in @AutoGen.OpenAI.OpenAIChatAgent.

> [!NOTE]
> You can find the complete sample code [here](https://github.com/microsoft/autogen/blob/main/dotnet/sample/AutoGen.SemanticKernel.Sample/Use_Kernel_Functions_With_Other_Agent.cs)

### Step 1: add using statement
[!code-csharp[](../../../sample/AutoGen.SemanticKernel.Sample/Use_Kernel_Functions_With_Other_Agent.cs?name=Using)]

### Step 2: create plugin

In this step, we create a simple plugin with a single `GetWeather` function that takes a location as input and returns the weather information for that location.

[!code-csharp[](../../../sample/AutoGen.SemanticKernel.Sample/Use_Kernel_Functions_With_Other_Agent.cs?name=Create_plugin)]

### Step 3: create OpenAIChatAgent and use the plugin

In this step, we firstly create a @AutoGen.SemanticKernel.KernelPluginMiddleware and register the previous plugin with it. The `KernelPluginMiddleware` will load the plugin and make the functions available for use in other agents. Followed by creating an @AutoGen.OpenAI.OpenAIChatAgent and register it with the `KernelPluginMiddleware`.

[!code-csharp[](../../../sample/AutoGen.SemanticKernel.Sample/Use_Kernel_Functions_With_Other_Agent.cs?name=Use_plugin)]

### Step 4: chat with OpenAIChatAgent

In this final step, we start the chat with the @AutoGen.OpenAI.OpenAIChatAgent by asking the weather in Seattle. The `OpenAIChatAgent` will use the `GetWeather` function from the plugin to get the weather information for Seattle.

[!code-csharp[](../../../sample/AutoGen.SemanticKernel.Sample/Use_Kernel_Functions_With_Other_Agent.cs?name=Send_message)]