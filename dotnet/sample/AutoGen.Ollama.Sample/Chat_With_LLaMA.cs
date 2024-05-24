// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_LLaMA.cs

using AutoGen.Core;
using AutoGen.Ollama.Extension;

namespace AutoGen.Ollama.Sample;

public class Chat_With_LLaMA
{
    public static async Task RunAsync()
    {
        using var httpClient = new HttpClient()
        {
            BaseAddress = new Uri("https://2xbvtxd1-11434.usw2.devtunnels.ms")
        };

        var ollamaAgent = new OllamaAgent(
            httpClient: httpClient,
            name: "ollama",
            modelName: "llama3:latest",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        var reply = await ollamaAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
    }
}
