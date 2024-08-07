// Copyright (c) Microsoft Corporation. All rights reserved.
// DotnetInteractiveKernelBuilderTest.cs

using AutoGen.DotnetInteractive.Extension;
using FluentAssertions;
using Xunit;

namespace AutoGen.DotnetInteractive.Tests;

public class DotnetInteractiveKernelBuilderTest
{
    [Fact]
    public async Task ItAddCSharpKernelTestAsync()
    {
        var kernel = DotnetInteractiveKernelBuilder
            .CreateEmptyBuilder()
            .AddCSharpKernel()
            .Build();

        var csharpCode = """
            #r "nuget:Microsoft.ML, 1.5.2"
            Console.WriteLine("Hello, World!");
            """;

        var result = await kernel.RunSubmitCodeCommandAsync(csharpCode, "C#");
        result.Should().Contain("Hello, World!");
    }

    [Fact]
    public async Task ItAddPowershellKernelTestAsync()
    {
        var kernel = DotnetInteractiveKernelBuilder
            .CreateEmptyBuilder()
            .AddPowershellKernel()
            .Build();

        var powershellCode = @"
            Write-Host 'Hello, World!'
            ";

        var result = await kernel.RunSubmitCodeCommandAsync(powershellCode, "pwsh");
        result.Should().Contain("Hello, World!");
    }

    [Fact]
    public async Task ItAddFSharpKernelTestAsync()
    {
        var kernel = DotnetInteractiveKernelBuilder
            .CreateEmptyBuilder()
            .AddFSharpKernel()
            .Build();

        var fsharpCode = """
            #r "nuget:Microsoft.ML, 1.5.2"
            printfn "Hello, World!"
            """;

        var result = await kernel.RunSubmitCodeCommandAsync(fsharpCode, "F#");
        result.Should().Contain("Hello, World!");
    }

    [Fact]
    public async Task ItAddPythonKernelTestAsync()
    {
        var kernel = DotnetInteractiveKernelBuilder
            .CreateEmptyBuilder()
            .AddPythonKernel("python3")
            .Build();

        var pythonCode = """
            %pip install numpy
            print('Hello, World!')
            """;

        var result = await kernel.RunSubmitCodeCommandAsync(pythonCode, "python");
        result.Should().Contain("Hello, World!");
    }
}
