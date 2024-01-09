// Copyright (c) Microsoft Corporation. All rights reserved.
// RunCodeSnippetCodeSnippet.cs

#region code_snippet_0_1
using AutoGen.DotnetInteractive;
#endregion code_snippet_0_1
namespace AutoGen.BasicSample.CodeSnippet;
public class RunCodeSnippetCodeSnippet
{
    public async Task CodeSnippet1()
    {
        IAgent agent = default;

        #region code_snippet_1_1
        var workingDirectory = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName());
        Directory.CreateDirectory(workingDirectory);
        var interactiveService = new InteractiveService(installingDirectory: workingDirectory);
        await interactiveService.StartAsync(workingDirectory: workingDirectory);
        #endregion code_snippet_1_1

        #region code_snippet_1_2
        // register dotnet code block execution hook to an arbitrary agent
        var dotnetCodeAgent = agent.RegisterDotnetCodeBlockExectionHook(interactiveService: interactiveService);

        var codeSnippet = @"
        ```csharp
        Console.WriteLine(""Hello World"");
        ```";

        await dotnetCodeAgent.SendAsync(codeSnippet);
        // output: Hello World
        #endregion code_snippet_1_2
    }
}
