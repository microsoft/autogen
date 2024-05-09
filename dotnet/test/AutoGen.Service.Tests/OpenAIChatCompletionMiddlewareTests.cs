// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionMiddlewareTests.cs

using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;
using Azure.Core.Pipeline;
using FluentAssertions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace AutoGen.Service.Tests;

public class OpenAIChatCompletionMiddlewareTests
{
    [Fact]
    public async Task ItReturnTextMessageWhenSendTextMessage()
    {
        var agent = new EchoAgent("test");
        var hostBuilder = CreateHostBuilder(agent);
        using var host = await hostBuilder.StartAsync();
        var client = host.GetTestClient();
        var openaiClient = CreateOpenAIClient(client);
        var openAIAgent = new OpenAIChatAgent(openaiClient, "test", "test")
            .RegisterMessageConnector();

        var response = await openAIAgent.SendAsync("Hey");

        response.GetContent().Should().Be("Hey");
        response.Should().BeOfType<TextMessage>();
        response.From.Should().Be("test");
    }

    private IHostBuilder CreateHostBuilder(IAgent agent)
    {
        return new HostBuilder()
            .ConfigureWebHost(webHost =>
            {
                webHost.UseTestServer();
                webHost.Configure(app =>
                {
                    app.UseAgentAsOpenAIChatCompletionEndpoint(agent);
                });
            });
    }

    private OpenAIClient CreateOpenAIClient(HttpClient client)
    {
        var clientOption = new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2024_02_15_Preview)
        {
            Transport = new HttpClientTransport(client),
        };
        return new OpenAIClient("api-key", clientOption);
    }
}
