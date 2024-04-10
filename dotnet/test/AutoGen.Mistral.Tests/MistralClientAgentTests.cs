// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClientAgentTests.cs

using System.Text.Json;
using AutoGen.Core;
using AutoGen.Mistral.Extension;
using AutoGen.Tests;
using FluentAssertions;

namespace AutoGen.Mistral.Tests;

public class MistralClientAgentTests
{
    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentChatCompletionTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var agent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "open-mistral-7b")
            .RegisterMessageConnector();

        var reply = await agent.SendAsync("What's the weather like today?");
        reply.Should().BeOfType<TextMessage>();
        reply.GetContent().Should().NotBeNullOrEmpty();
        reply.From.Should().Be(agent.Name);
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentJsonModeTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);

        var agent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            jsonOutput: true,
            systemMessage: "You are a helpful assistant that convert input to json object",
            model: "open-mistral-7b",
            randomSeed: 0)
            .RegisterMessageConnector();

        var reply = await agent.SendAsync("name: John, age: 41, email: g123456@gmail.com");
        reply.Should().BeOfType<TextMessage>();
        reply.GetContent().Should().NotBeNullOrEmpty();
        reply.From.Should().Be(agent.Name);
        var json = reply.GetContent();
        var person = JsonSerializer.Deserialize<Person>(json!);

        person.Should().NotBeNull();
        person!.Name.Should().Be("John");
        person!.Age.Should().Be(41);
        person!.Email.Should().Be("g123456@gmail.com");
    }
}
