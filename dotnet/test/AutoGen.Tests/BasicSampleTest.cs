// Copyright (c) Microsoft Corporation. All rights reserved.
// BasicSampleTest.cs

using System;
using System.IO;
using System.Threading.Tasks;
using AutoGen.BasicSample;
using Xunit.Abstractions;

namespace AutoGen.Tests;

public class BasicSampleTest
{
    private readonly ITestOutputHelper _output;

    public BasicSampleTest(ITestOutputHelper output)
    {
        _output = output;
        Console.SetOut(new ConsoleWriter(_output));
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task AssistantAgentTestAsync()
    {
        await Example01_AssistantAgent.RunAsync();
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task TwoAgentMathClassTestAsync()
    {
        await Example02_TwoAgent_MathChat.RunAsync();
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task AgentFunctionCallTestAsync()
    {
        await Example03_Agent_FunctionCall.RunAsync();
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralClientAgent_TokenCount()
    {
        await Example14_MistralClientAgent_TokenCount.RunAsync();
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task DynamicGroupChatCalculateFibonacciAsync()
    {
        await Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunAsync();
        await Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunWorkflowAsync();
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task DalleAndGPT4VTestAsync()
    {
        await Example05_Dalle_And_GPT4V.RunAsync();
    }

    [ApiKeyFact("OPENAI_API_KEY")]
    public async Task GPT4ImageMessage()
    {
        await Example15_GPT4V_BinaryDataImageMessage.RunAsync();
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
