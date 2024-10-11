// Copyright (c) Microsoft Corporation. All rights reserved.
// Example14_MistralClientAgent_TokenCount.cs

#region using_statements
using AutoGen.Core;
using AutoGen.Mistral;
#endregion using_statements
using FluentAssertions;

namespace AutoGen.BasicSample;

public class Example14_MistralClientAgent_TokenCount
{
    #region token_counter_middleware
    public class MistralAITokenCounterMiddleware : IMiddleware
    {
        private readonly List<ChatCompletionResponse> responses = new List<ChatCompletionResponse>();
        public string? Name => nameof(MistralAITokenCounterMiddleware);

        public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
        {
            var reply = await agent.GenerateReplyAsync(context.Messages, context.Options, cancellationToken);

            if (reply is IMessage<ChatCompletionResponse> message)
            {
                responses.Add(message.Content);
            }

            return reply;
        }

        public int GetCompletionTokenCount()
        {
            return responses.Sum(r => r.Usage.CompletionTokens);
        }
    }
    #endregion token_counter_middleware

    public static async Task RunAsync()
    {
        #region create_mistral_client_agent
        var apiKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new Exception("Missing MISTRAL_API_KEY environment variable.");
        var mistralClient = new MistralClient(apiKey);
        var agent = new MistralClientAgent(
            client: mistralClient,
            name: "assistant",
            model: MistralAIModelID.OPEN_MISTRAL_7B);
        #endregion create_mistral_client_agent

        #region register_middleware
        var tokenCounterMiddleware = new MistralAITokenCounterMiddleware();
        var mistralMessageConnector = new MistralChatMessageConnector();
        var agentWithTokenCounter = agent
            .RegisterMiddleware(tokenCounterMiddleware)
            .RegisterMiddleware(mistralMessageConnector)
            .RegisterPrintMessage();
        #endregion register_middleware

        #region chat_with_agent
        await agentWithTokenCounter.SendAsync("write a long, tedious story");
        Console.WriteLine($"Completion token count: {tokenCounterMiddleware.GetCompletionTokenCount()}");
        tokenCounterMiddleware.GetCompletionTokenCount().Should().BeGreaterThan(0);
        #endregion chat_with_agent
    }
}
