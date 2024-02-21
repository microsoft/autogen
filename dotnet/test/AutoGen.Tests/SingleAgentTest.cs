// Copyright (c) Microsoft Corporation. All rights reserved.
// SingleAgentTest.cs

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AutoGen.OpenAI;
using Azure.AI.OpenAI;
using FluentAssertions;
using Xunit;
using Xunit.Abstractions;

namespace AutoGen.Tests
{
    public partial class SingleAgentTest
    {
        private ITestOutputHelper _output;
        public SingleAgentTest(ITestOutputHelper output)
        {
            _output = output;
        }

        private ILLMConfig CreateAzureOpenAIGPT35TurboConfig()
        {
            var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new ArgumentException("AZURE_OPENAI_API_KEY is not set");
            var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new ArgumentException("AZURE_OPENAI_ENDPOINT is not set");
            return new AzureOpenAIConfig(endpoint, "gpt-35-turbo-16k", key);
        }

        private ILLMConfig CreateOpenAIGPT4VisionConfig()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            return new OpenAIConfig(key, "gpt-4-vision-preview");
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task GPTAgentTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();

            var agent = new GPTAgent("gpt", "You are a helpful AI assistant", config);

            await UpperCaseTest(agent);
            await UpperCaseStreamingTestAsync(agent);
        }

        [ApiKeyFact("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task GPTAgentVisionTestAsync()
        {
            var visionConfig = this.CreateOpenAIGPT4VisionConfig();
            var visionAgent = new GPTAgent(
                name: "gpt",
                systemMessage: "You are a helpful AI assistant",
                config: visionConfig,
                temperature: 0);

            var gpt3Config = this.CreateAzureOpenAIGPT35TurboConfig();
            var gpt3Agent = new GPTAgent(
                name: "gpt3",
                systemMessage: "You are a helpful AI assistant, return highest label from conversation",
                config: gpt3Config,
                temperature: 0,
                functions: new[] { this.GetHighestLabelFunction },
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { nameof(GetHighestLabel), this.GetHighestLabelWrapper },
                });


            var oaiMessage = new ChatRequestUserMessage(
                new ChatMessageTextContentItem("which label has the highest inference cost"),
                new ChatMessageImageContentItem(new Uri(@"https://raw.githubusercontent.com/microsoft/autogen/main/website/blog/2023-04-21-LLM-tuning-math/img/level2algebra.png")));

            var message = oaiMessage.ToMessage();
            var response = await visionAgent.SendAsync(message);
            response.From.Should().Be(visionAgent.Name);

            var labelResponse = await gpt3Agent.SendAsync(response);
            labelResponse.From.Should().Be(gpt3Agent.Name);
            labelResponse.Content.Should().Be("[HIGHEST_LABEL] gpt-4 (n=5) green");
            labelResponse.FunctionName.Should().Be(nameof(GetHighestLabel));
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task GPTFunctionCallAgentTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();
            var agentWithFunction = new GPTAgent("gpt", "You are a helpful AI assistant", config, 0, functions: new[] { this.EchoAsyncFunction });

            await EchoFunctionCallTestAsync(agentWithFunction);
            await UpperCaseTest(agentWithFunction);
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task AssistantAgentFunctionCallTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();

            var llmConfig = new ConversableAgentConfig
            {
                Temperature = 0,
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

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task AssistantAgentFunctionCallSelfExecutionTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();
            var llmConfig = new ConversableAgentConfig
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

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT")]
        public async Task GPTAgentFunctionCallSelfExecutionTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();
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

            await EchoFunctionCallExecutionStreamingTestAsync(agent);
            await EchoFunctionCallExecutionTestAsync(agent);
            await UpperCaseTest(agent);
        }

        /// <summary>
        /// echo when asked.
        /// </summary>
        /// <param name="message">message to echo</param>
        [FunctionAttribute]
        public async Task<string> EchoAsync(string message)
        {
            return $"[ECHO] {message}";
        }

        /// <summary>
        /// return the label name with hightest inference cost
        /// </summary>
        /// <param name="labelName"></param>
        /// <returns></returns>
        [FunctionAttribute]
        public async Task<string> GetHighestLabel(string labelName, string color)
        {
            return $"[HIGHEST_LABEL] {labelName} {color}";
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

        private async Task EchoFunctionCallExecutionStreamingTestAsync(IStreamingAgent agent)
        {
            var message = new Message(Role.System, "You are a helpful AI assistant that echo whatever user says");
            var helloWorld = new Message(Role.User, "echo Hello world");
            var option = new GenerateReplyOptions
            {
                Temperature = 0,
            };
            var replyStream = await agent.GenerateStreamingReplyAsync(messages: new Message[] { message, helloWorld }, option);
            var answer = "[ECHO] Hello world";
            Message? finalReply = default;
            await foreach (var reply in replyStream)
            {
                reply.Role.Should().Be(Role.Assistant);
                reply.From.Should().Be(agent.Name);

                finalReply = reply;

                var formatted = reply.FormatMessage();
                _output.WriteLine(formatted);
            }

            finalReply!.Content.Should().Be(answer);
            finalReply!.Role.Should().Be(Role.Assistant);
            finalReply!.From.Should().Be(agent.Name);
            finalReply!.FunctionName.Should().Be(nameof(EchoAsync));
        }

        private async Task UpperCaseTest(IAgent agent)
        {
            var message = new Message(Role.System, "You are a helpful AI assistant that convert user message to upper case");
            var uppCaseMessage = new Message(Role.User, "abcdefg");

            var reply = await agent.SendAsync(chatHistory: new Message[] { message, uppCaseMessage });

            reply.Content.Should().Be("ABCDEFG");
            reply.Role.Should().Be(Role.Assistant);
            reply.From.Should().Be(agent.Name);
        }

        private async Task UpperCaseStreamingTestAsync(IStreamingAgent agent)
        {
            var message = new Message(Role.System, "You are a helpful AI assistant that convert user message to upper case");
            var helloWorld = new Message(Role.User, "a b c d e f g h i j k l m n");
            var option = new GenerateReplyOptions
            {
                Temperature = 0,
            };
            var replyStream = await agent.GenerateStreamingReplyAsync(messages: new Message[] { message, helloWorld }, option);
            var answer = "A B C D E F G H I J K L M N";
            Message? finalReply = default;
            await foreach (var reply in replyStream)
            {
                reply.Role.Should().Be(Role.Assistant);
                reply.From.Should().Be(agent.Name);

                // the content should be part of the answer
                reply.Content.Should().Be(answer.Substring(0, reply.Content!.Length));
                finalReply = reply;

                // print the message
                var formatted = reply.FormatMessage();
                _output.WriteLine(formatted);
            }

            finalReply!.Content.Should().Be(answer);
            finalReply!.Role.Should().Be(Role.Assistant);
            finalReply!.From.Should().Be(agent.Name);
        }
    }
}
