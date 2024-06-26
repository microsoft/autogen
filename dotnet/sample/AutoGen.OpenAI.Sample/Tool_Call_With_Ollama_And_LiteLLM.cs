// Copyright (c) Microsoft Corporation. All rights reserved.
// Tool_Call_With_Ollama_And_LiteLLM.cs

using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;
using Azure.Core.Pipeline;

namespace AutoGen.OpenAI.Sample;

public partial class Function
{
    [Function]
    public async Task<string> GetWeatherAsync(string city)
    {
        return await Task.FromResult("The weather in " + city + " is 72 degrees and sunny.");
    }
}
public class Tool_Call_With_Ollama_And_LiteLLM
{
    public static async Task RunAsync()
    {
        #region Create_Agent
        var liteLLMUrl = "http://localhost:4000";
        using var httpClient = new HttpClient(new CustomHttpClientHandler(liteLLMUrl));
        var option = new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2024_04_01_Preview)
        {
            Transport = new HttpClientTransport(httpClient),
        };

        var functions = new Function();
        var functionMiddleware = new FunctionCallMiddleware(
            functions: [functions.GetWeatherAsyncFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { functions.GetWeatherAsyncFunctionContract.Name!, functions.GetWeatherAsyncWrapper },
            });

        // api-key is not required for local server
        // so you can use any string here
        var openAIClient = new OpenAIClient("api-key", option);

        var agent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            name: "assistant",
            modelName: "placeholder",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterMiddleware(functionMiddleware)
            .RegisterPrintMessage();

        var reply = await agent.SendAsync("what's the weather in new york");
        #endregion Create_Agent
    }
}
