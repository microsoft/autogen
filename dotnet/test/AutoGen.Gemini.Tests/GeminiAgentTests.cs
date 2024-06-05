// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiAgentTests.cs

using AutoGen.Tests;
using Google.Cloud.AIPlatform.V1;
using AutoGen.Core;
using FluentAssertions;
using AutoGen.Gemini.Extension;
using static Google.Cloud.AIPlatform.V1.Part;
namespace AutoGen.Gemini.Tests;

public class GeminiAgentTests
{
    private readonly Functions functions = new Functions();
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
    public async Task VertexGeminiAgentGenerateReplyWithToolsAsync()
    {
        var location = "us-central1";
        var project = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID") ?? throw new InvalidOperationException("GCP_VERTEX_PROJECT_ID is not set.");
        var model = "gemini-1.5-flash-001";
        var tools = new Tool[]
        {
            functions.GetWeatherAsyncFunctionContract.ToTool(),
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
}
