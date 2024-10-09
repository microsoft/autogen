`AutoGen` provides a built-in feature to run code snippet from agent response. Currently the following languages are supported:
- dotnet

More languages will be supported in the future.

## What is a code snippet?
A code snippet in agent response is a code block with a language identifier. For example:

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_3)]

## Why running code snippet is useful?
The ability of running code snippet can greatly extend the ability of an agent. Because it enables agent to resolve tasks by writing code and run it, which is much more powerful than just returning a text response.

For example, in data analysis scenario, agent can resolve tasks like "What is the average of the sales amount of the last 7 days?" by firstly write a code snippet to query the sales amount of the last 7 days, then calculate the average and then run the code snippet to get the result.

> [!WARNING]
> Running arbitrary code snippet from agent response could bring risks to your system. Using this feature with caution.

## Use dotnet interactive kernel to execute code snippet?
The built-in feature of running dotnet code snippet is provided by [dotnet-interactive](https://github.com/dotnet/interactive). To run dotnet code snippet, you need to install the following package to your project, which provides the intergraion with dotnet-interactive:

```xml
<PackageReference Include="AutoGen.DotnetInteractive" />
```

Then you can use @AutoGen.DotnetInteractive.DotnetInteractiveKernelBuilder* to create a in-process dotnet-interactive composite kernel with C# and F# kernels.
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_1)]

After that, use @AutoGen.DotnetInteractive.Extension.RunSubmitCodeCommandAsync* method to run code snippet. The method will return the result of the code snippet.
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_2)]

## Run python code snippet
To run python code, firstly you need to have python installed on your machine, then you need to set up ipykernel and jupyter in your environment.

```bash
pip install ipykernel
pip install jupyter
```

After `ipykernel` and `jupyter` are installed, you can confirm the ipykernel is installed correctly by running the following command:

```bash
jupyter kernelspec list
```

The output should contain all available kernels, including `python3`.

```bash
Available kernels:
    python3    /usr/local/share/jupyter/kernels/python3
    ...
```

Then you can add the python kernel to the dotnet-interactive composite kernel by calling `AddPythonKernel` method.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/RunCodeSnippetCodeSnippet.cs?name=code_snippet_1_4)]

## Further reading
You can refer to the following examples for running code snippet in agentic workflow:
- Dynamic_GroupChat_Coding_Task:  [![](https://img.shields.io/badge/Open%20on%20Github-grey?logo=github)](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AutoGen.BasicSample/Example04_Dynamic_GroupChat_Coding_Task.cs)
- Dynamic_GroupChat_Calculate_Fibonacci: [![](https://img.shields.io/badge/Open%20on%20Github-grey?logo=github)](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AutoGen.BasicSample/Example07_Dynamic_GroupChat_Calculate_Fibonacci.cs)
