// Copyright (c) Microsoft Corporation. All rights reserved.
// Tool_Call_With_Ollama_And_LiteLLM.cs

using AutoGen.Core;
using AutoGen.OpenAI.V1;
using AutoGen.OpenAI.V1.Extension;
using Azure.AI.OpenAI;
using Azure.Core.Pipeline;

namespace AutoGen.OpenAI.Sample;

#region Function
public partial class Function
{
    [Function]
    public async Task<string> GetWeatherAsync(string city)
    {
        return await Task.FromResult("The weather in " + city + " is 72 degrees and sunny.");
    }
}
#endregion Function

public class Tool_Call_With_Ollama_And_LiteLLM
{
    public static async Task RunAsync()
    {
        // Before running this code, make sure you have
        // - Ollama:
        //  - Install dolphincoder:latest in Ollama
        //  - Ollama running on http://localhost:11434
        // - LiteLLM
        //  - Install LiteLLM
        //  - Start LiteLLM with the following command:
        //    - litellm --model ollama_chat/dolphincoder --port 4000

        # region Create_tools
        var functions = new Function();
        var functionMiddleware = new FunctionCallMiddleware(
            functions: [functions.GetWeatherAsyncFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { functions.GetWeatherAsyncFunctionContract.Name!, functions.GetWeatherAsyncWrapper },
            });
        #endregion Create_tools
        #region Create_Agent
        var liteLLMUrl = "http://localhost:4000";
        using var httpClient = new HttpClient(new CustomHttpClientHandler(liteLLMUrl));
        var option = new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2024_04_01_Preview)
        {
            Transport = new HttpClientTransport(httpClient),
        };

        // api-key is not required for local server
        // so you can use any string here
        var openAIClient = new OpenAIClient("api-key", option);

        var agent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            name: "assistant",
            modelName: "dolphincoder:latest",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterMiddleware(functionMiddleware)
            .RegisterPrintMessage();

        var reply = await agent.SendAsync("what's the weather in new york");
        #endregion Create_Agent
    }
}
