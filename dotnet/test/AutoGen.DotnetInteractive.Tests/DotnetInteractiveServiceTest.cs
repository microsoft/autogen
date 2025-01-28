// Copyright (c) Microsoft Corporation. All rights reserved.
// DotnetInteractiveServiceTest.cs

using FluentAssertions;
using Xunit;
using Xunit.Abstractions;

namespace AutoGen.DotnetInteractive.Tests;

[Collection("Sequential")]
public class DotnetInteractiveServiceTest : IDisposable
{
    private ITestOutputHelper _output;
    private InteractiveService _interactiveService;
    private string _workingDir;

    public DotnetInteractiveServiceTest(ITestOutputHelper output)
    {
        _output = output;
        _workingDir = Path.Combine(Path.GetTempPath(), "test", Path.GetRandomFileName());
        if (!Directory.Exists(_workingDir))
        {
            Directory.CreateDirectory(_workingDir);
        }

        _interactiveService = new InteractiveService(_workingDir);
        var isRunning = _interactiveService.StartAsync(_workingDir, default).Result;
        isRunning.Should().BeTrue();
    }

    public void Dispose()
    {
        _interactiveService.Dispose();
    }

    [Fact]
    public async Task ItRunCSharpCodeSnippetTestsAsync()
    {
        // test code snippet
        var hello_world = @"
Console.WriteLine(""hello world"");
";

        await this.TestCSharpCodeSnippet(_interactiveService, hello_world, "hello world");
        await this.TestCSharpCodeSnippet(
            _interactiveService,
            code: @"
Console.WriteLine(""hello world""
",
            expectedOutput: "Error: (2,32): error CS1026: ) expected");

        await this.TestCSharpCodeSnippet(
            service: _interactiveService,
            code: "throw new Exception();",
            expectedOutput: "Error: System.Exception: Exception of type 'System.Exception' was thrown");
    }

    [Fact]
    public async Task ItRunPowershellScriptTestsAsync()
    {
        // test power shell
        var ps = @"Write-Output ""hello world""";
        await this.TestPowershellCodeSnippet(_interactiveService, ps, "hello world");
    }

    private async Task TestPowershellCodeSnippet(InteractiveService service, string code, string expectedOutput)
    {
        var result = await service.SubmitPowershellCodeAsync(code, CancellationToken.None);
        result.Should().StartWith(expectedOutput);
    }

    private async Task TestCSharpCodeSnippet(InteractiveService service, string code, string expectedOutput)
    {
        var result = await service.SubmitCSharpCodeAsync(code, CancellationToken.None);
        result.Should().StartWith(expectedOutput);
    }
}
