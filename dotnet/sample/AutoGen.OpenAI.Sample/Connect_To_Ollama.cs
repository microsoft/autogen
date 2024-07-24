// Copyright (c) Microsoft Corporation. All rights reserved.
// Connect_To_Ollama.cs

#region using_statement
using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using OpenAI;
using OpenAI.Chat;
#endregion using_statement

namespace AutoGen.OpenAI;

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
        var option = new OpenAIClientOptions()
        {
            Endpoint = new Uri("http://localhost:11434"),
        };

        float? temperature = null;
        var chatOption = new ChatCompletionOptions()
        {
            Temperature = 0.7f,
            MaxTokens = 100,
            TopP = 1,
        };

        // api-key is not required for local server
        // so you can use any string here
        var openAIClient = new OpenAIClient("api-key", option);
        var model = "llama3";
        var chatClient = openAIClient.GetChatClient(model);

        var agent = new OpenAIChatAgent(
            chatClient: chatClient,
            name: "assistant",
            systemMessage: "You are a helpful assistant designed to output JSON.",
            options: chatOption)
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion create_agent

        #region send_message
        await agent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion send_message
    }
}
