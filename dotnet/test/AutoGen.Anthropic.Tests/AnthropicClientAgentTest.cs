// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicClientAgentTest.cs

using AutoGen.Anthropic.Extensions;
using AutoGen.Anthropic.Utils;
using AutoGen.Tests;
using Xunit.Abstractions;

namespace AutoGen.Anthropic;

public class AnthropicClientAgentTest
{
    private readonly ITestOutputHelper _output;

    public AnthropicClientAgentTest(ITestOutputHelper output) => _output = output;

    [ApiKeyFact("ANTHROPIC_API_KEY")]
    public async Task AnthropicAgentChatCompletionTestAsync()
    {
        var client = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, AnthropicTestUtils.ApiKey);

        var agent = new AnthropicClientAgent(
            client,
            name: "AnthropicAgent",
            AnthropicConstants.Claude3Haiku).RegisterMessageConnector();

        var singleAgentTest = new SingleAgentTest(_output);
        await singleAgentTest.UpperCaseTestAsync(agent);
        await singleAgentTest.UpperCaseStreamingTestAsync(agent);
    }
}
