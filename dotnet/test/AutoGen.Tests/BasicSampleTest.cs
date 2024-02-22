// Copyright (c) Microsoft Corporation. All rights reserved.
// BasicSampleTest.cs

using System;
using System.IO;
using System.Threading.Tasks;
using Xunit.Abstractions;

namespace AutoGen.Tests
{
    public class BasicSampleTest
    {
        private readonly ITestOutputHelper _output;

        public BasicSampleTest(ITestOutputHelper output)
        {
            _output = output;
            Console.SetOut(new ConsoleWriter(_output));
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task AssistantAgentTestAsync()
        {
            await Example01_AssistantAgent.RunAsync();
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task TwoAgentMathClassTestAsync()
        {
            await Example02_TwoAgent_MathChat.RunAsync();
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task AgentFunctionCallTestAsync()
        {
            var instance = new Example03_Agent_FunctionCall();
            await instance.RunAsync();
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task DynamicGroupChatGetMLNetPRTestAsync()
        {
            await Example04_Dynamic_GroupChat_Coding_Task.RunAsync();
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task DynamicGroupChatCalculateFibonacciAsync()
        {
            await Example07_Dynamic_GroupChat_Calculate_Fibonacci.RunAsync();
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task DalleAndGPT4VTestAsync()
        {
            await Example05_Dalle_And_GPT4V.RunAsync();
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
}
