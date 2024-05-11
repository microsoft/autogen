`AutoGen` provides a built-in feature to run code snippet from agent response. Currently the following languages are supported:
- dotnet

More languages will be supported in the future.

## What is a code snippet?
A code snippet in agent response is a code block with a language identifier. For example:

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_3)]

## Why running code snippet is useful?
The ability of running code snippet can greatly extend the ability of an agent. Because it enables agent to resolve tasks by writing code and run it, which is much more powerful than just returning a text response.

For example, in data analysis scenario, agent can resolve tasks like "What is the average of the sales amount of the last 7 days?" by firstly write a code snippet to query the sales amount of the last 7 days, then calculate the average and then run the code snippet to get the result.

> [!WARNING]
> Running arbitrary code snippet from agent response could bring risks to your system. Using this feature with caution.

## How to run dotnet code snippet?
The built-in feature of running dotnet code snippet is provided by [dotnet-interactive](https://github.com/dotnet/interactive). To run dotnet code snippet, you need to install the following package to your project, which provides the intergraion with dotnet-interactive:

> [!Note]
> The `AutoGen.DotnetInteractive` has a dependency on `Microsoft.DotNet.Interactive.VisualStudio` which is not available on nuget.org. To restore the dependency, you need to add the following package source to your project:
> ```bash
> https://pkgs.dev.azure.com/dnceng/public/_packaging/dotnet-tools/nuget/v3/index.json
> ```

```xml
<PackageReference Include="AutoGen.DotnetInteractive" />
```

Then you can use @AutoGen.DotnetInteractive.AgentExtension.RegisterDotnetCodeBlockExectionHook(AutoGen.IAgent,InteractiveService,System.String,System.String) to register a `reply hook` to run dotnet code snippet. The hook will check if a csharp code snippet is present in the most recent message from history, and run the code snippet if it is present.

The following code snippet shows how to register a dotnet code snippet execution hook:

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_0_1)]
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_1)]
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_2)]
