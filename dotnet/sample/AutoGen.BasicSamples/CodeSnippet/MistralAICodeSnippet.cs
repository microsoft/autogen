// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralAICodeSnippet.cs

#region using_statement
using AutoGen.Mistral;
using AutoGen.Core;
#endregion using_statement

namespace AutoGen.BasicSample.CodeSnippet;

internal class MistralAICodeSnippet
{
    public async Task CreateMistralAIClientAsync()
    {
        #region create_mistral_agent
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new Exception("Missing MISTRAL_API_KEY environment variable");
        var client = new MistralClient(apiKey: apiKey);
        var agent = new MistralClientAgent(
            client: client,
            name: "MistralAI",
            model: MistralAIModelID.OPEN_MISTRAL_7B);

        await agent.SendAsync("Hello, how are you?");
        #endregion create_mistral_agent
    }
}
