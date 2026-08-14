// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelAgentTest.cs

using AutoGen.Core;
using AutoGen.SemanticKernel.Extension;
using AutoGen.Tests;
using FluentAssertions;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Agents;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Xunit;

namespace AutoGen.SemanticKernel.Tests;

[Trait("Category", "UnitV1")]
public partial class SemanticKernelAgentTest
{
    /// <summary>
    /// Get the weather for a location.
    /// </summary>
    /// <param name="location">location</param>
    /// <returns></returns>
    [Function]
    public async Task<string> GetWeatherAsync(string location)
    {
        return $"The weather in {location} is sunny.";
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task BasicConversationTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key);

        var kernel = builder.Build();
        var skAgent = new SemanticKernelAgent(kernel, "assistant");

        await TestBasicConversationAsync(skAgent);
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task BasicConversationTestWithKeyedServiceAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var modelServiceId = "my-service-id";
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key, modelServiceId);

        var kernel = builder.Build();
        var skAgent = new SemanticKernelAgent(kernel, "assistant", modelServiceId: modelServiceId);

        await TestBasicConversationAsync(skAgent);
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task SemanticKernelChatMessageContentConnectorTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key);

        var kernel = builder.Build();

        var skAgent = new SemanticKernelAgent(kernel, "assistant")
            .RegisterMessageConnector();

        var messages = new IMessage[]
        {
            MessageEnvelope.Create(new ChatMessageContent(AuthorRole.Assistant, "Hello")),
            new TextMessage(Role.Assistant, "Hello", from: "user"), new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, "Hello", from: "user"),
                ],
                from: "user"),
        };

        foreach (var message in messages)
        {
            var reply = await skAgent.SendAsync(message);

            reply.Should().BeOfType<TextMessage>();
            reply.As<TextMessage>().From.Should().Be("assistant");
        }

        // test streaming
        foreach (var message in messages)
        {
            var reply = skAgent.GenerateStreamingReplyAsync([message]);

            await foreach (var streamingMessage in reply)
            {
                streamingMessage.Should().BeOfType<TextMessageUpdate>();
                streamingMessage.As<TextMessageUpdate>().From.Should().Be("assistant");
            }
        }
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task SemanticKernelPluginTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key);

        var parameters = this.GetWeatherAsyncFunctionContract.Parameters!.Select(p => new KernelParameterMetadata(p.Name!)
        {
            Description = p.Description,
            DefaultValue = p.DefaultValue,
            IsRequired = p.IsRequired,
            ParameterType = p.ParameterType,
        });
        var function = KernelFunctionFactory.CreateFromMethod(this.GetWeatherAsync, this.GetWeatherAsyncFunctionContract.Name, this.GetWeatherAsyncFunctionContract.Description, parameters);
        builder.Plugins.AddFromFunctions("plugins", [function]);
        var kernel = builder.Build();

        var skAgent = new SemanticKernelAgent(kernel, "assistant")
            .RegisterMessageConnector();

        skAgent.StreamingMiddlewares.Count().Should().Be(1);

        var question = "What is the weather in Seattle?";
        var reply = await skAgent.SendAsync(question);

        reply.GetContent()!.ToLower().Should().Contain("seattle");
        reply.GetContent()!.ToLower().Should().Contain("sunny");
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task BasicSkChatCompletionAgentConversationTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key);

        var kernel = builder.Build();
        var agent = new ChatCompletionAgent()
        {
            Kernel = kernel,
            Name = "assistant",
            Instructions = "You are a helpful AI assistant"
        };

        var skAgent = new SemanticKernelChatCompletionAgent(agent);

        var chatMessageContent = MessageEnvelope.Create(new ChatMessageContent(AuthorRole.Assistant, "Hello"));
        var reply = await skAgent.SendAsync(chatMessageContent);

        reply.Should().BeOfType<MessageEnvelope<ChatMessageContent>>();
        reply.As<MessageEnvelope<ChatMessageContent>>().From.Should().Be("assistant");
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task SkChatCompletionAgentChatMessageContentConnectorTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key);

        var kernel = builder.Build();

        var connector = new SemanticKernelChatMessageContentConnector();
        var agent = new ChatCompletionAgent()
        {
            Kernel = kernel,
            Name = "assistant",
            Instructions = "You are a helpful AI assistant"
        };
        var skAgent = new SemanticKernelChatCompletionAgent(agent)
            .RegisterMiddleware(connector);

        var messages = new IMessage[]
        {
            MessageEnvelope.Create(new ChatMessageContent(AuthorRole.Assistant, "Hello")),
            new TextMessage(Role.Assistant, "Hello", from: "user"), new MultiModalMessage(Role.Assistant,
                [
                    new TextMessage(Role.Assistant, "Hello", from: "user"),
                ],
                from: "user"),
        };

        foreach (var message in messages)
        {
            var reply = await skAgent.SendAsync(message);

            reply.Should().BeOfType<TextMessage>();
            reply.As<TextMessage>().From.Should().Be("assistant");
        }
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task SkChatCompletionAgentPluginTestAsync()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var builder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(deploymentName, endpoint, key);

        var parameters = this.GetWeatherAsyncFunctionContract.Parameters!.Select(p => new KernelParameterMetadata(p.Name!)
        {
            Description = p.Description,
            DefaultValue = p.DefaultValue,
            IsRequired = p.IsRequired,
            ParameterType = p.ParameterType,
        });
        var function = KernelFunctionFactory.CreateFromMethod(this.GetWeatherAsync, this.GetWeatherAsyncFunctionContract.Name, this.GetWeatherAsyncFunctionContract.Description, parameters);
        builder.Plugins.AddFromFunctions("plugins", [function]);
        var kernel = builder.Build();

        var agent = new ChatCompletionAgent()
        {
            Kernel = kernel,
            Name = "assistant",
            Instructions = "You are a helpful AI assistant",
            Arguments = new KernelArguments(new OpenAIPromptExecutionSettings()
            {
                ToolCallBehavior = ToolCallBehavior.AutoInvokeKernelFunctions
            })
        };
        var skAgent =
            new SemanticKernelChatCompletionAgent(agent).RegisterMiddleware(
                new SemanticKernelChatMessageContentConnector());

        var question = "What is the weather in Seattle?";
        var reply = await skAgent.SendAsync(question);

        reply.GetContent()!.ToLower().Should().Contain("seattle");
        reply.GetContent()!.ToLower().Should().Contain("sunny");
    }

    private static async Task TestBasicConversationAsync(SemanticKernelAgent agent)
    {
        var chatMessageContent = MessageEnvelope.Create(new ChatMessageContent(AuthorRole.Assistant, "Hello"));
        var reply = await agent.SendAsync(chatMessageContent);

        reply.Should().BeOfType<MessageEnvelope<ChatMessageContent>>();
        reply.As<MessageEnvelope<ChatMessageContent>>().From.Should().Be("assistant");

        // test streaming
        var streamingReply = agent.GenerateStreamingReplyAsync(new[] { chatMessageContent });

        await foreach (var streamingMessage in streamingReply)
        {
            streamingMessage.Should().BeOfType<MessageEnvelope<StreamingChatMessageContent>>();
            streamingMessage.As<MessageEnvelope<StreamingChatMessageContent>>().From.Should().Be("assistant");
        }
    }
}
