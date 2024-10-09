// Copyright (c) Microsoft Corporation. All rights reserved.
// KernelFunctionMiddlewareTests.cs

using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using AutoGen.Tests;
using Azure;
using Azure.AI.OpenAI;
using FluentAssertions;
using Microsoft.SemanticKernel;

namespace AutoGen.SemanticKernel.Tests;

public class KernelFunctionMiddlewareTests
{
    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task ItRegisterKernelFunctionMiddlewareFromTestPluginTests()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deployName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var openaiClient = new AzureOpenAIClient(
            endpoint: new Uri(endpoint),
            credential: new AzureKeyCredential(key));

        var kernel = new Kernel();
        var plugin = kernel.ImportPluginFromType<TestPlugin>();
        var kernelFunctionMiddleware = new KernelPluginMiddleware(kernel, plugin);

        var agent = new OpenAIChatAgent(openaiClient.GetChatClient(deployName), "assistant")
            .RegisterMessageConnector()
            .RegisterMiddleware(kernelFunctionMiddleware);

        var reply = await agent.SendAsync("what's the status of the light?");
        reply.GetContent().Should().Be("off");
        reply.Should().BeOfType<ToolCallAggregateMessage>();
        if (reply is ToolCallAggregateMessage aggregateMessage)
        {
            var toolCallMessage = aggregateMessage.Message1;
            toolCallMessage.ToolCalls.Should().HaveCount(1);
            toolCallMessage.ToolCalls[0].FunctionName.Should().Be("GetState");

            var toolCallResultMessage = aggregateMessage.Message2;
            toolCallResultMessage.ToolCalls.Should().HaveCount(1);
            toolCallResultMessage.ToolCalls[0].Result.Should().Be("off");
        }

        reply = await agent.SendAsync("change the status of the light to on");
        reply.GetContent().Should().Be("The status of the light is now on");
        reply.Should().BeOfType<ToolCallAggregateMessage>();
        if (reply is ToolCallAggregateMessage aggregateMessage1)
        {
            var toolCallMessage = aggregateMessage1.Message1;
            toolCallMessage.ToolCalls.Should().HaveCount(1);
            toolCallMessage.ToolCalls[0].FunctionName.Should().Be("ChangeState");

            var toolCallResultMessage = aggregateMessage1.Message2;
            toolCallResultMessage.ToolCalls.Should().HaveCount(1);
        }
    }

    [ApiKeyFact("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOY_NAME")]
    public async Task ItRegisterKernelFunctionMiddlewareFromMethodTests()
    {
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var key = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var deployName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? throw new Exception("Please set AZURE_OPENAI_DEPLOY_NAME environment variable.");
        var openaiClient = new AzureOpenAIClient(
            endpoint: new Uri(endpoint),
            credential: new AzureKeyCredential(key));

        var kernel = new Kernel();
        var getWeatherMethod = kernel.CreateFunctionFromMethod((string location) => $"The weather in {location} is sunny.", functionName: "GetWeather", description: "Get the weather for a location.");
        var createPersonObjectMethod = kernel.CreateFunctionFromMethod((string name, string email, int age) => new Person(name, email, age), functionName: "CreatePersonObject", description: "Creates a person object.");
        var plugin = kernel.ImportPluginFromFunctions("plugin", [getWeatherMethod, createPersonObjectMethod]);
        var kernelFunctionMiddleware = new KernelPluginMiddleware(kernel, plugin);

        var agent = new OpenAIChatAgent(chatClient: openaiClient.GetChatClient(deployName), "assistant")
            .RegisterMessageConnector()
            .RegisterMiddleware(kernelFunctionMiddleware);

        var reply = await agent.SendAsync("what's the weather in Seattle?");
        reply.GetContent().Should().Be("The weather in Seattle is sunny.");
        reply.Should().BeOfType<ToolCallAggregateMessage>();
        if (reply is ToolCallAggregateMessage getWeatherMessage)
        {
            var toolCallMessage = getWeatherMessage.Message1;
            toolCallMessage.ToolCalls.Should().HaveCount(1);
            toolCallMessage.ToolCalls[0].FunctionName.Should().Be("GetWeather");

            var toolCallResultMessage = getWeatherMessage.Message2;
            toolCallResultMessage.ToolCalls.Should().HaveCount(1);
        }

        reply = await agent.SendAsync("Create a person object with name: John, email: 12345@gmail.com, age: 30");
        reply.GetContent().Should().Be("Name: John, Email: 12345@gmail.com, Age: 30");
        reply.Should().BeOfType<ToolCallAggregateMessage>();
        if (reply is ToolCallAggregateMessage createPersonObjectMessage)
        {
            var toolCallMessage = createPersonObjectMessage.Message1;
            toolCallMessage.ToolCalls.Should().HaveCount(1);
            toolCallMessage.ToolCalls[0].FunctionName.Should().Be("CreatePersonObject");

            var toolCallResultMessage = createPersonObjectMessage.Message2;
            toolCallResultMessage.ToolCalls.Should().HaveCount(1);
        }
    }
}

public class Person
{
    public Person(string name, string email, int age)
    {
        this.Name = name;
        this.Email = email;
        this.Age = age;
    }

    public string Name { get; set; }
    public string Email { get; set; }
    public int Age { get; set; }

    public override string ToString()
    {
        return $"Name: {this.Name}, Email: {this.Email}, Age: {this.Age}";
    }
}
