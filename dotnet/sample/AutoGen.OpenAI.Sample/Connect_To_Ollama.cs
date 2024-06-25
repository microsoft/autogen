// Copyright (c) Microsoft Corporation. All rights reserved.
// Example16_OpenAIChatAgent_ConnectToThirdPartyBackend.cs
#region using_statement
using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;
using Azure.Core.Pipeline;
#endregion using_statement

namespace AutoGen.OpenAI.Sample;

#region CustomHttpClientHandler
public sealed class CustomHttpClientHandler : HttpClientHandler
{
    private string _modelServiceUrl;

    public CustomHttpClientHandler(string modelServiceUrl)
    {
        _modelServiceUrl = modelServiceUrl;
    }

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        request.RequestUri = new Uri($"{_modelServiceUrl}{request.RequestUri.PathAndQuery}");

        return base.SendAsync(request, cancellationToken);
    }
}
#endregion CustomHttpClientHandler

public class Connect_To_Ollama
{
    public static async Task RunAsync()
    {
        #region create_agent
        using var client = new HttpClient(new CustomHttpClientHandler("http://localhost:11434"));
        var option = new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2024_04_01_Preview)
        {
            Transport = new HttpClientTransport(client),
        };

        // api-key is not required for local server
        // so you can use any string here
        var openAIClient = new OpenAIClient("api-key", option);
        var model = "llama3";

        var agent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            name: "assistant",
            modelName: model,
            systemMessage: "You are a helpful assistant designed to output JSON.",
            seed: 0)
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion create_agent

        #region send_message
        await agent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion send_message
    }
}
