`AutoGen` provides a built-in feature to run code snippet from agent response. Currently the following languages are supported:
- dotnet

More languages will be supported in the future.

## What is a code snippet?
A code snippet in agent response is a code block with a language identifier. For example:

```csharp
// This is a cs code snippet
```

```python
# This is a python code snippet
```

## Why running code snippet is useful?
The ability of running code snippet can greatly extend the ability of an agent. Because it enables agent to resolve tasks by writing code and run it, which is much more powerful than just returning a text response.

For example, in data analysis scenario, agent can resolve tasks like "What is the average of the sales amount of the last 7 days?" by firstly write a code snippet to query the sales amount of the last 7 days, then calculate the average and then run the code snippet to get the result.

> [!WARNING]
> Running arbitrary code snippet from agent response could bring risks to your system. Using this feature with caution.

## How to run dotnet code snippet?
The built-in feature of running dotnet code snippet is provided by [dotnet-interactive](https://github.com/dotnet/interactive). To run dotnet code snippet, you need to install the following package to your project, which provides the intergraion with dotnet-interactive:

```xml
<PackageReference Include="AutoGen.DotnetInteractive" />
```

Then you can use `RegisterDotnetCodeBlockExectionHook` to register an `auto reply hook` to run dotnet code snippet. The hook will be called when a dotnet code snippet is detected in chat message. The hook will run the code snippet and return the result as agent reply.

> [!NOTE]
> `auto reply hook` is an agent hook which will be triggered automantically when a certain condition is met. For more information about available agent hooks, please refer to [Auto reply hook](./Register-auto-reply.md), [Preprocess hook](./Preprocess-hook.md) and [Postprocess hook](./Postprocess-hook.md).

The following code snippet shows how to register a dotnet code snippet execution hook:

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_0_1)]
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_1)]
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_2)]
