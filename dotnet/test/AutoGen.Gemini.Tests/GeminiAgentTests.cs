// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiAgentTests.cs

using AutoGen.Tests;
using Google.Cloud.AIPlatform.V1;
using AutoGen.Core;
using FluentAssertions;
using AutoGen.Gemini.Extension;
using static Google.Cloud.AIPlatform.V1.Part;
using Xunit.Abstractions;
namespace AutoGen.Gemini.Tests;

public class GeminiAgentTests
{
    private readonly Functions functions = new Functions();
    private readonly ITestOutputHelper _output;

    public GeminiAgentTests(ITestOutputHelper output)
    {
        _output = output;
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task VertexGeminiAgentGenerateReplyForTextContentAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";

        var textContent = new Content
        {
            Role = "user",
            Parts =
            {
                new Part
                {
                    Text = "Hello",
                }
            }
        };

        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location,
            systemMessage: "You are a helpful AI assistant");
        var message = MessageEnvelope.Create(textContent, from: agent.Name);

        var completion = await agent.SendAsync(message);

        completion.Should().BeOfType<MessageEnvelope<GenerateContentResponse>>();
        completion.From.Should().Be(agent.Name);

        var response = ((MessageEnvelope<GenerateContentResponse>)completion).Content;
        response.Should().NotBeNull();
        response.Candidates.Count.Should().BeGreaterThan(0);
        response.Candidates[0].Content.Parts[0].Text.Should().NotBeNullOrEmpty();
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task VertexGeminiAgentGenerateStreamingReplyForTextContentAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";

        var textContent = new Content
        {
            Role = "user",
            Parts =
            {
                new Part
                {
                    Text = "Hello",
                }
            }
        };

        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location,
            systemMessage: "You are a helpful AI assistant");
        var message = MessageEnvelope.Create(textContent, from: agent.Name);

        var completion = agent.GenerateStreamingReplyAsync([message]);
        var chunks = new List<IMessage>();
        IMessage finalReply = null!;

        await foreach (var item in completion)
        {
            item.Should().NotBeNull();
            item.From.Should().Be(agent.Name);
            var streamingMessage = (IMessage<GenerateContentResponse>)item;
            streamingMessage.Content.Candidates.Should().NotBeNullOrEmpty();
            chunks.Add(item);
            finalReply = item;
        }

        chunks.Count.Should().BeGreaterThan(0);
        finalReply.Should().NotBeNull();
        finalReply.Should().BeOfType<MessageEnvelope<GenerateContentResponse>>();
        var response = ((MessageEnvelope<GenerateContentResponse>)finalReply).Content;
        response.UsageMetadata.CandidatesTokenCount.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task VertexGeminiAgentGenerateReplyWithToolsAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";
        var tools = new Tool[]
        {
            new Tool
            {
                FunctionDeclarations = {
                    functions.GetWeatherAsyncFunctionContract.ToFunctionDeclaration(),
                },
            },
            new Tool
            {
                FunctionDeclarations =
                {
                    functions.GetMoviesFunctionContract.ToFunctionDeclaration(),
                },
            },
        };

        var textContent = new Content
        {
            Role = "user",
            Parts =
            {
                new Part
                {
                    Text = "what's the weather in seattle",
                }
            }
        };

        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location,
            systemMessage: "You are a helpful AI assistant",
            tools: tools,
            toolConfig: new ToolConfig()
            {
                FunctionCallingConfig = new FunctionCallingConfig()
                {
                    Mode = FunctionCallingConfig.Types.Mode.Auto,
                }
            });

        var message = MessageEnvelope.Create(textContent, from: agent.Name);

        var completion = await agent.SendAsync(message);

        completion.Should().BeOfType<MessageEnvelope<GenerateContentResponse>>();
        completion.From.Should().Be(agent.Name);

        var response = ((MessageEnvelope<GenerateContentResponse>)completion).Content;
        response.Should().NotBeNull();
        response.Candidates.Count.Should().BeGreaterThan(0);
        response.Candidates[0].Content.Parts[0].DataCase.Should().Be(DataOneofCase.FunctionCall);
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task VertexGeminiAgentGenerateStreamingReplyWithToolsAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";
        var tools = new Tool[]
        {
            new Tool
            {
                FunctionDeclarations = { functions.GetWeatherAsyncFunctionContract.ToFunctionDeclaration() },
            },
        };

        var textContent = new Content
        {
            Role = "user",
            Parts =
            {
                new Part
                {
                    Text = "what's the weather in seattle",
                }
            }
        };

        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location,
            systemMessage: "You are a helpful AI assistant",
            tools: tools,
            toolConfig: new ToolConfig()
            {
                FunctionCallingConfig = new FunctionCallingConfig()
                {
                    Mode = FunctionCallingConfig.Types.Mode.Auto,
                }
            });

        var message = MessageEnvelope.Create(textContent, from: agent.Name);

        var chunks = new List<IMessage>();
        IMessage finalReply = null!;

        var completion = agent.GenerateStreamingReplyAsync([message]);

        await foreach (var item in completion)
        {
            item.Should().NotBeNull();
            item.From.Should().Be(agent.Name);
            var streamingMessage = (IMessage<GenerateContentResponse>)item;
            streamingMessage.Content.Candidates.Should().NotBeNullOrEmpty();
            if (streamingMessage.Content.Candidates[0].FinishReason != Candidate.Types.FinishReason.Stop)
            {
                streamingMessage.Content.Candidates[0].Content.Parts[0].DataCase.Should().Be(DataOneofCase.FunctionCall);
            }
            chunks.Add(item);
            finalReply = item;
        }

        chunks.Count.Should().BeGreaterThan(0);
        finalReply.Should().NotBeNull();
        finalReply.Should().BeOfType<MessageEnvelope<GenerateContentResponse>>();
        var response = ((MessageEnvelope<GenerateContentResponse>)finalReply).Content;
        response.UsageMetadata.CandidatesTokenCount.Should().BeGreaterThan(0);
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task GeminiAgentUpperCaseTestAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";
        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location)
            .RegisterMessageConnector();

        var singleAgentTest = new SingleAgentTest(_output);
        await singleAgentTest.UpperCaseStreamingTestAsync(agent);
        await singleAgentTest.UpperCaseTestAsync(agent);
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task GeminiAgentEchoFunctionCallTestAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";
        var singleAgentTest = new SingleAgentTest(_output);
        var echoFunctionContract = singleAgentTest.EchoAsyncFunctionContract;
        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location,
            tools:
            [
                new Tool
                {
                    FunctionDeclarations = { echoFunctionContract.ToFunctionDeclaration() },
                },
            ])
            .RegisterMessageConnector();

        await singleAgentTest.EchoFunctionCallTestAsync(agent);
    }

    [ApiKeyFact("GCP_VERTEX_PROJECT_ID")]
    public async Task GeminiAgentEchoFunctionCallExecutionTestAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";
        var singleAgentTest = new SingleAgentTest(_output);
        var echoFunctionContract = singleAgentTest.EchoAsyncFunctionContract;
        var functionMiddleware = new FunctionCallMiddleware(
            functions: [echoFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>()
            {
                { echoFunctionContract.Name!, singleAgentTest.EchoAsyncWrapper },
            });

        var agent = new GeminiChatAgent(
            name: "assistant",
            model: model,
            project: project,
            location: location)
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionMiddleware);

        await singleAgentTest.EchoFunctionCallExecutionStreamingTestAsync(agent);
        await singleAgentTest.EchoFunctionCallExecutionTestAsync(agent);
    }
}
