// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// DotnetInteractiveStdioKernelConnectorTests.cs

using AutoGen.DotnetInteractive.Extension;
using FluentAssertions;
using Microsoft.DotNet.Interactive;
using Xunit;
using Xunit.Abstractions;

namespace AutoGen.DotnetInteractive.Tests;

[Collection("Sequential")]
public class DotnetInteractiveStdioKernelConnectorTests : IDisposable
{
    private string _workingDir;
    private Kernel kernel;
    public DotnetInteractiveStdioKernelConnectorTests(ITestOutputHelper output)
    {
        _workingDir = Path.Combine(Path.GetTempPath(), "test", Path.GetRandomFileName());
        if (!Directory.Exists(_workingDir))
        {
            Directory.CreateDirectory(_workingDir);
        }

        kernel = DotnetInteractiveKernelBuilder
            .CreateKernelBuilder(_workingDir)
            .RestoreDotnetInteractive()
            .AddPythonKernel("python3")
            .BuildAsync().Result;
    }


    [Fact]
    public async Task ItAddCSharpKernelTestAsync()
    {
        var csharpCode = """
            #r "nuget:Microsoft.ML, 1.5.2"
            var str = "Hello" + ", World!";
            Console.WriteLine(str);
            """;

        var result = await this.kernel.RunSubmitCodeCommandAsync(csharpCode, "csharp");
        result.Should().Contain("Hello, World!");
    }

    [Fact]
    public async Task ItAddPowershellKernelTestAsync()
    {
        var powershellCode = @"
            Write-Host 'Hello, World!'
            ";

        var result = await this.kernel.RunSubmitCodeCommandAsync(powershellCode, "pwsh");
        result.Should().Contain("Hello, World!");
    }

    [Fact]
    public async Task ItAddFSharpKernelTestAsync()
    {
        var fsharpCode = """
            printfn "Hello, World!"
            """;

        var result = await this.kernel.RunSubmitCodeCommandAsync(fsharpCode, "fsharp");
        result.Should().Contain("Hello, World!");
    }

    [Fact]
    public async Task ItAddPythonKernelTestAsync()
    {
        var pythonCode = """
            %pip install numpy
            str = 'Hello' + ', World!'
            print(str)
            """;

        var result = await this.kernel.RunSubmitCodeCommandAsync(pythonCode, "python");
        result.Should().Contain("Hello, World!");
    }

    public void Dispose()
    {
        this.kernel.Dispose();
    }
}
