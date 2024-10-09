// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClientAgentTests.cs

using System.Text.Json;
using AutoGen.Core;
using AutoGen.Mistral.Extension;
using AutoGen.Tests;
using FluentAssertions;
using Xunit.Abstractions;

namespace AutoGen.Mistral.Tests;

public partial class MistralClientAgentTests
{
    private ITestOutputHelper _output;

    public MistralClientAgentTests(ITestOutputHelper output)
    {
        _output = output;
    }

    [Function]
    public async Task<string> GetWeather(string city)
    {
        return $"The weather in {city} is sunny.";
    }

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
        var singleAgentTest = new SingleAgentTest(_output);
        await singleAgentTest.UpperCaseTestAsync(agent);
        await singleAgentTest.UpperCaseStreamingTestAsync(agent);
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

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentFunctionCallMessageTest()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);
        var agent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "mistral-small-latest",
            randomSeed: 0)
            .RegisterMessageConnector();

        var weatherFunctionArgumets = """
            {
                "city": "Seattle"
            }
            """;
        var functionCallResult = await this.GetWeatherWrapper(weatherFunctionArgumets);
        var toolCall = new ToolCall(this.GetWeatherFunctionContract.Name!, weatherFunctionArgumets)
        {
            ToolCallId = "012345678", // Mistral AI requires the tool call id to be a length of 9
            Result = functionCallResult,
        };
        IMessage[] chatHistory = [
            new TextMessage(Role.User, "what's the weather in Seattle?"),
            new ToolCallMessage([toolCall], from: agent.Name),
            new ToolCallResultMessage([toolCall], weatherFunctionArgumets),
        ];

        var reply = await agent.SendAsync(chatHistory: chatHistory);

        reply.Should().BeOfType<TextMessage>();
        reply.GetContent().Should().Be("The weather in Seattle is sunny.");
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentTwoAgentFunctionCallTest()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);
        var twoAgentTest = new TwoAgentTest(_output);
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [twoAgentTest.GetWeatherFunctionContract]);
        var functionCallAgent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "mistral-small-latest",
            randomSeed: 0)
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var functionCallMiddlewareExecutorMiddleware = new FunctionCallMiddleware(
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { twoAgentTest.GetWeatherFunctionContract.Name!, twoAgentTest.GetWeatherWrapper }
            });
        var executorAgent = new MistralClientAgent(
            client: client,
            name: "ExecutorAgent",
            model: "mistral-small-latest",
            randomSeed: 0)
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddlewareExecutorMiddleware);
        await twoAgentTest.TwoAgentGetWeatherFunctionCallTestAsync(executorAgent, functionCallAgent);
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentFunctionCallMiddlewareMessageTest()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [this.GetWeatherFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { this.GetWeatherFunctionContract.Name!, this.GetWeatherWrapper }
            });
        var functionCallAgent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "mistral-small-latest",
            randomSeed: 0)
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);

        var question = new TextMessage(Role.User, "what's the weather in Seattle?");
        var reply = await functionCallAgent.SendAsync(question);
        reply.Should().BeOfType<ToolCallAggregateMessage>();

        // resend the reply to the same agent so it can generate the final response
        // because the reply's from is the agent's name
        // in this case, the aggregate message will be converted to tool call message + tool call result message
        var finalReply = await functionCallAgent.SendAsync(chatHistory: [question, reply]);
        finalReply.Should().BeOfType<TextMessage>();
        finalReply.GetContent().Should().Be("The weather in Seattle is sunny.");

        var anotherAgent = new MistralClientAgent(
            client: client,
            name: "AnotherMistralClientAgent",
            model: "mistral-small-latest",
            randomSeed: 0)
            .RegisterMessageConnector();

        // if send the reply to another agent with different name,
        // the reply will be interpreted as a plain text message
        var plainTextReply = await anotherAgent.SendAsync(chatHistory: [reply, question]);
        plainTextReply.Should().BeOfType<TextMessage>();
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentFunctionCallAutoInvokeTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);
        var singleAgentTest = new SingleAgentTest(_output);
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [singleAgentTest.EchoAsyncFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { singleAgentTest.EchoAsyncFunctionContract.Name!, singleAgentTest.EchoAsyncWrapper }
            });
        var agent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "mistral-small-latest",
            toolChoice: ToolChoiceEnum.Any,
            randomSeed: 0)
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);
        await singleAgentTest.EchoFunctionCallExecutionTestAsync(agent);
        await singleAgentTest.EchoFunctionCallExecutionStreamingTestAsync(agent);
    }

    [ApiKeyFact("MISTRAL_API_KEY")]
    public async Task MistralAgentFunctionCallTestAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new InvalidOperationException("MISTRAL_API_KEY is not set.");
        var client = new MistralClient(apiKey: apiKey);
        var singleAgentTest = new SingleAgentTest(_output);
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [singleAgentTest.EchoAsyncFunctionContract, this.GetWeatherFunctionContract]);
        var agent = new MistralClientAgent(
            client: client,
            name: "MistralClientAgent",
            model: "mistral-small-latest",
            toolChoice: ToolChoiceEnum.Any,
            systemMessage: "You are a helpful assistant that can call functions",
            randomSeed: 0)
            .RegisterMessageConnector()
            .RegisterStreamingMiddleware(functionCallMiddleware);
        await singleAgentTest.EchoFunctionCallTestAsync(agent);

        // streaming test
        var question = new TextMessage(Role.User, "what's the weather in Seattle?");
        IMessage? finalReply = null;

        await foreach (var reply in agent.GenerateStreamingReplyAsync([question]))
        {
            reply.From.Should().Be(agent.Name);
            if (reply is IMessage message)
            {
                finalReply = message;
            }
        }

        finalReply.Should().NotBeNull();
        finalReply.Should().BeOfType<ToolCallMessage>();
    }
}
