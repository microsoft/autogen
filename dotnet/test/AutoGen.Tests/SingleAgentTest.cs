// Copyright (c) Microsoft Corporation. All rights reserved.
// SingleAgentTest.cs

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using AutoGen.LMStudio;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
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
            var deployName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new ArgumentException("AZURE_OPENAI_DEPLOY_NAME is not set");
            return new AzureOpenAIConfig(endpoint, deployName, key);
        }

        private ILLMConfig CreateOpenAIGPT4VisionConfig()
        {
            var key = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new ArgumentException("OPENAI_API_KEY is not set");
            return new OpenAIConfig(key, "gpt-4-vision-preview");
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
        public async Task GPTAgentTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();

            var agent = new GPTAgent("gpt", "You are a helpful AI assistant", config);

            await UpperCaseTestAsync(agent);
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
                functions: new[] { this.GetHighestLabelFunctionContract.ToOpenAIFunctionDefinition() },
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { nameof(GetHighestLabel), this.GetHighestLabelWrapper },
                });

            var imageUri = new Uri(@"https://microsoft.github.io/autogen/assets/images/level2algebra-659ba95286432d9945fc89e84d606797.png");
            var oaiMessage = new ChatRequestUserMessage(
                new ChatMessageTextContentItem("which label has the highest inference cost"),
                new ChatMessageImageContentItem(imageUri));
            var multiModalMessage = new MultiModalMessage(Role.User,
                [
                    new TextMessage(Role.User, "which label has the highest inference cost", from: "user"),
                    new ImageMessage(Role.User, imageUri, from: "user"),
                ],
                from: "user");

            var imageMessage = new ImageMessage(Role.User, imageUri, from: "user");

            string imagePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ApprovalTests", "square.png");
            ImageMessage imageMessageData;
            using (var fs = new FileStream(imagePath, FileMode.Open, FileAccess.Read))
            {
                var ms = new MemoryStream();
                await fs.CopyToAsync(ms);
                ms.Seek(0, SeekOrigin.Begin);
                var imageData = await BinaryData.FromStreamAsync(ms, "image/png");
                imageMessageData = new ImageMessage(Role.Assistant, imageData, from: "user");
            }

            IMessage[] messages = [
                MessageEnvelope.Create(oaiMessage),
                multiModalMessage,
                imageMessage,
                imageMessageData
                ];

            foreach (var message in messages)
            {
                var response = await visionAgent.SendAsync(message);
                response.From.Should().Be(visionAgent.Name);

                var labelResponse = await gpt3Agent.SendAsync(response);
                labelResponse.From.Should().Be(gpt3Agent.Name);
                labelResponse.GetToolCalls()!.First().FunctionName.Should().Be(nameof(GetHighestLabel));
            }
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
        public async Task GPTFunctionCallAgentTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();
            var agentWithFunction = new GPTAgent("gpt", "You are a helpful AI assistant", config, 0, functions: new[] { this.EchoAsyncFunctionContract.ToOpenAIFunctionDefinition() });

            await EchoFunctionCallTestAsync(agentWithFunction);
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
        public async Task AssistantAgentFunctionCallTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();

            var llmConfig = new ConversableAgentConfig
            {
                Temperature = 0,
                FunctionContracts = new[]
                {
                    this.EchoAsyncFunctionContract,
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
        }

        [Fact]
        public async Task ItCreateAssistantAgentFromLMStudioConfigAsync()
        {
            var host = "http://localhost";
            var port = 8080;
            var lmStudioConfig = new LMStudioConfig(host, port);

            var assistantAgent = new AssistantAgent(
                name: "assistant",
                llmConfig: new ConversableAgentConfig()
                {
                    ConfigList = [lmStudioConfig],
                });

            assistantAgent.Name.Should().Be("assistant");
            assistantAgent.InnerAgent.Should().BeOfType<LMStudioAgent>();
        }

        [ApiKeyFact("LMStudio_ENDPOINT")]
        public async Task ItTestAssistantAgentFromLMStudioConfigAsync()
        {
            var Uri = Environment.GetEnvironmentVariable("LMStudio_ENDPOINT") ?? throw new ArgumentException("LMStudio_ENDPOINT is not set");
            var lmStudioConfig = new LMStudioConfig(new Uri(Uri));

            var assistantAgent = new AssistantAgent(
                name: "assistant",
                llmConfig: new ConversableAgentConfig()
                {
                    ConfigList = [lmStudioConfig],
                });

            assistantAgent.Name.Should().Be("assistant");
            assistantAgent.InnerAgent.Should().BeOfType<LMStudioAgent>();
            await this.UpperCaseTestAsync(assistantAgent);
        }


        [Fact]
        public async Task AssistantAgentDefaultReplyTestAsync()
        {
            var assistantAgent = new AssistantAgent(
                llmConfig: null,
                name: "assistant",
                defaultReply: "hello world");

            var reply = await assistantAgent.SendAsync("hi");

            reply.GetContent().Should().Be("hello world");
            reply.GetRole().Should().Be(Role.Assistant);
            reply.From.Should().Be(assistantAgent.Name);
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
        public async Task AssistantAgentFunctionCallSelfExecutionTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();
            var llmConfig = new ConversableAgentConfig
            {
                FunctionContracts = new[]
                {
                    this.EchoAsyncFunctionContract,
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
        }

        [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
        public async Task GPTAgentFunctionCallSelfExecutionTestAsync()
        {
            var config = this.CreateAzureOpenAIGPT35TurboConfig();
            var agent = new GPTAgent(
                name: "gpt",
                systemMessage: "You are a helpful AI assistant",
                config: config,
                temperature: 0,
                functions: new[] { this.EchoAsyncFunctionContract.ToOpenAIFunctionDefinition() },
                functionMap: new Dictionary<string, Func<string, Task<string>>>
                {
                    { nameof(EchoAsync), this.EchoAsyncWrapper },
                });

            await EchoFunctionCallExecutionStreamingTestAsync(agent);
            await EchoFunctionCallExecutionTestAsync(agent);
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

        public async Task EchoFunctionCallTestAsync(IAgent agent)
        {
            //var message = new TextMessage(Role.System, "You are a helpful AI assistant that call echo function");
            var helloWorld = new TextMessage(Role.User, "echo Hello world");

            var reply = await agent.SendAsync(chatHistory: new[] { helloWorld });

            reply.From.Should().Be(agent.Name);
            reply.GetToolCalls()!.First().FunctionName.Should().Be(nameof(EchoAsync));
        }

        public async Task EchoFunctionCallExecutionTestAsync(IAgent agent)
        {
            //var message = new TextMessage(Role.System, "You are a helpful AI assistant that echo whatever user says");
            var helloWorld = new TextMessage(Role.User, "echo Hello world");

            var reply = await agent.SendAsync(chatHistory: new[] { helloWorld });

            reply.GetContent().Should().Be("[ECHO] Hello world");
            reply.From.Should().Be(agent.Name);
            reply.Should().BeOfType<ToolCallAggregateMessage>();
        }

        public async Task EchoFunctionCallExecutionStreamingTestAsync(IStreamingAgent agent)
        {
            //var message = new TextMessage(Role.System, "You are a helpful AI assistant that echo whatever user says");
            var helloWorld = new TextMessage(Role.User, "echo Hello world");
            var option = new GenerateReplyOptions
            {
                Temperature = 0,
            };
            var replyStream = agent.GenerateStreamingReplyAsync(messages: new[] { helloWorld }, option);
            var answer = "[ECHO] Hello world";
            IMessage? finalReply = default;
            await foreach (var reply in replyStream)
            {
                reply.From.Should().Be(agent.Name);
                finalReply = reply;
            }

            if (finalReply is ToolCallAggregateMessage aggregateMessage)
            {
                var toolCallResultMessage = aggregateMessage.Message2;
                toolCallResultMessage.ToolCalls.First().Result.Should().Be(answer);
                toolCallResultMessage.From.Should().Be(agent.Name);
                toolCallResultMessage.ToolCalls.First().FunctionName.Should().Be(nameof(EchoAsync));
            }
            else
            {
                throw new Exception("unexpected message type");
            }
        }

        public async Task UpperCaseTestAsync(IAgent agent)
        {
            var message = new TextMessage(Role.User, "Please convert abcde to upper case.");

            var reply = await agent.SendAsync(chatHistory: new[] { message });

            reply.GetContent().Should().Contain("ABCDE");
            reply.From.Should().Be(agent.Name);
        }

        public async Task UpperCaseStreamingTestAsync(IStreamingAgent agent)
        {
            var message = new TextMessage(Role.User, "Please convert 'hello world' to upper case");
            var option = new GenerateReplyOptions
            {
                Temperature = 0,
            };
            var replyStream = agent.GenerateStreamingReplyAsync(messages: new[] { message }, option);
            var answer = "HELLO WORLD";
            TextMessage? finalReply = default;
            await foreach (var reply in replyStream)
            {
                if (reply is TextMessageUpdate update)
                {
                    update.From.Should().Be(agent.Name);

                    if (finalReply is null)
                    {
                        finalReply = new TextMessage(update);
                    }
                    else
                    {
                        finalReply.Update(update);
                    }

                    continue;
                }
                else if (reply is TextMessage textMessage)
                {
                    finalReply = textMessage;
                    continue;
                }

                throw new Exception("unexpected message type");
            }

            finalReply!.Content.Should().Contain(answer);
            finalReply!.Role.Should().Be(Role.Assistant);
            finalReply!.From.Should().Be(agent.Name);
        }
    }
}
