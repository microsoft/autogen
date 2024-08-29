// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAISampleTest.cs

using System;
using System.IO;
using System.Threading.Tasks;
using AutoGen.OpenAI.Sample;
using AutoGen.Tests;
using Xunit.Abstractions;

namespace AutoGen.OpenAI.Tests;

public class OpenAISampleTest
{
    private readonly ITestOutputHelper _output;

    public OpenAISampleTest(ITestOutputHelper output)
    {
        _output = output;
        Console.SetOut(new ConsoleWriter(_output));
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task Structural_OutputAsync()
    {
        await Structural_Output.RunAsync();
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task Use_Json_ModeAsync()
    {
        await Use_Json_Mode.RunAsync();
    }

    public class ConsoleWriter : StringWriter
    {
        private ITestOutputHelper output;
        public ConsoleWriter(ITestOutputHelper output)
        {
            this.output = output;
        }

        public override void WriteLine(string? m)
        {
            output.WriteLine(m);
        }
    }
}
