// Copyright (c) Microsoft Corporation. All rights reserved.
// SingleAgentTest.cs

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using FluentAssertions;
using Microsoft.SemanticKernel.AI.ChatCompletion;
using Xunit;

namespace AutoGen.Tests
{
    public partial class SingleAgentTest
    {
        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task GPTAgentTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            var config = new OpenAIConfig(key, "gpt-3.5-turbo");

            var agent = new GPTAgent("gpt", "You are a helpful AI assistant", config, 0);

            await UpperCaseTest(agent);
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task GPTFunctionCallAgentTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            var config = new OpenAIConfig(key, "gpt-3.5-turbo");
            var agentWithFunction = new GPTAgent("gpt", "You are a helpful AI assistant", config, 0, functions: new[] { this.EchoAsyncFunction });

            await EchoFunctionCallTestAsync(agentWithFunction);
            await UpperCaseTest(agentWithFunction);
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task AssistantAgentFunctionCallTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            var config = new OpenAIConfig(key, "gpt-3.5-turbo");

            var llmConfig = new AssistantAgentConfig
            {
                FunctionDefinitions = new[]
                {
                    this.EchoAsyncFunction,
                },
                ConfigList = new[]
                {
                    config,
                },
            };

            var assistantAgent = new AssistantAgent(
                name: "assistant",
                llmConfig: llmConfig);

            await EchoFunctionCallTestAsync(assistantAgent);
            await UpperCaseTest(assistantAgent);
        }

        [Fact]
        public async Task AssistantAgentDefaultReplyTestAsync()
        {
            var assistantAgent = new AssistantAgent(
                llmConfig: null,
                name: "assistant",
                defaultReply: "hello world");

            var reply = await assistantAgent.SendAsync("hi");

            reply.Content.Should().Be("hello world");
            reply.Role.Should().Be(Role.Assistant);
            reply.From.Should().Be(assistantAgent.Name);
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task AssistantAgentFunctionCallSelfExecutionTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            var config = new OpenAIConfig(key, "gpt-3.5-turbo");
            var llmConfig = new AssistantAgentConfig
            {
                FunctionDefinitions = new[]
                {
                    this.EchoAsyncFunction,
                },
                ConfigList = new[]
                {
                    config,
                },
            };
            var assistantAgent = new AssistantAgent(
                name: "assistant",
                llmConfig: llmConfig,
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { nameof(EchoAsync), this.EchoAsyncWrapper },
                });

            await EchoFunctionCallExecutionTestAsync(assistantAgent);
            await UpperCaseTest(assistantAgent);
        }

        [ApiKeyFact("OPENAI_API_KEY")]
        public async Task GPTAgentFunctionCallSelfExecutionTestAsync()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            var config = new OpenAIConfig(key, "gpt-3.5-turbo");
            var agent = new GPTAgent(
                name: "gpt",
                systemMessage: "You are a helpful AI assistant",
                config: config,
                temperature: 0,
                functions: new[] { this.EchoAsyncFunction },
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { nameof(EchoAsync), this.EchoAsyncWrapper },
                });
            await EchoFunctionCallExecutionTestAsync(agent);
            await UpperCaseTest(agent);
        }

        /// <summary>
        /// echo when asked.
        /// </summary>
        /// <param name="message">message to echo</param>
        [FunctionAttribution]
        public async Task<string> EchoAsync(string message)
        {
            return $"[ECHO] {message}";
        }

        private async Task EchoFunctionCallTestAsync(IAgent agent)
        {
            var message = new Message(Role.System, "You are a helpful AI assistant that call echo function");
            var helloWorld = new Message(Role.User, "echo Hello world");

            var reply = await agent.SendAsync(chatHistory: new Message[] { message, helloWorld });

            reply.Role.Should().Be(Role.Assistant);
            reply.From.Should().Be(agent.Name);
            reply.FunctionName.Should().Be(nameof(EchoAsync));
        }

        private async Task EchoFunctionCallExecutionTestAsync(IAgent agent)
        {
            var message = new Message(Role.System, "You are a helpful AI assistant that echo whatever user says");
            var helloWorld = new Message(Role.User, "echo Hello world");

            var reply = await agent.SendAsync(chatHistory: new Message[] { message, helloWorld });

            reply.Content.Should().Be("[ECHO] Hello world");
            reply.Role.Should().Be(Role.Assistant);
            reply.From.Should().Be(agent.Name);
            reply.FunctionName.Should().Be(nameof(EchoAsync));
        }

        private async Task UpperCaseTest(IAgent agent)
        {
            var message = new Message(Role.System, "You are a helpful AI assistant that convert user message to upper case");
            var helloWorld = new Message(Role.User, "abcdefg");

            var reply = await agent.SendAsync(chatHistory: new Message[] { message, helloWorld });

            reply.Content.Should().Be("ABCDEFG");
            reply.Role.Should().Be(Role.Assistant);
            reply.From.Should().Be(agent.Name);
        }
    }
}
