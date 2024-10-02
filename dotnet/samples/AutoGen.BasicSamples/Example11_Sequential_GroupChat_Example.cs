// Copyright (c) Microsoft Corporation. All rights reserved.
// Example11_Sequential_GroupChat_Example.cs

#region using_statement
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using AutoGen.SemanticKernel;
using AutoGen.SemanticKernel.Extension;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Plugins.Web;
using Microsoft.SemanticKernel.Plugins.Web.Bing;
#endregion using_statement

namespace AutoGen.BasicSample;

public partial class Sequential_GroupChat_Example
{
    public static async Task<IAgent> CreateBingSearchAgentAsync()
    {
        #region CreateBingSearchAgent
        var config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var apiKey = config.ApiKey;
        var kernelBuilder = Kernel.CreateBuilder()
            .AddAzureOpenAIChatCompletion(config.DeploymentName, config.Endpoint, apiKey);
        var bingApiKey = Environment.GetEnvironmentVariable("BING_API_KEY") ?? throw new Exception("BING_API_KEY environment variable is not set");
        var bingSearch = new BingConnector(bingApiKey);
        var webSearchPlugin = new WebSearchEnginePlugin(bingSearch);
        kernelBuilder.Plugins.AddFromObject(webSearchPlugin);

        var kernel = kernelBuilder.Build();
        var kernelAgent = new SemanticKernelAgent(
            kernel: kernel,
            name: "bing-search",
            systemMessage: """
            You search results from Bing and return it as-is.
            You put the original search result between ```bing and ```

            e.g.
            ```bing
            xxx
            ```
            """)
            .RegisterMessageConnector()
            .RegisterPrintMessage(); // pretty print the message

        return kernelAgent;
        #endregion CreateBingSearchAgent
    }

    public static async Task<IAgent> CreateSummarizerAgentAsync()
    {
        #region CreateSummarizerAgent
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var openAIClientAgent = new OpenAIChatAgent(
            chatClient: gpt4o,
            name: "summarizer",
            systemMessage: "You summarize search result from bing in a short and concise manner");

        return openAIClientAgent
            .RegisterMessageConnector()
            .RegisterPrintMessage(); // pretty print the message
        #endregion CreateSummarizerAgent
    }

    public static async Task RunAsync()
    {
        #region Sequential_GroupChat_Example
        var userProxyAgent = new UserProxyAgent(
            name: "user",
            humanInputMode: HumanInputMode.ALWAYS)
            .RegisterPrintMessage();

        var bingSearchAgent = await CreateBingSearchAgentAsync();
        var summarizerAgent = await CreateSummarizerAgentAsync();

        var groupChat = new RoundRobinGroupChat(
            agents: [userProxyAgent, bingSearchAgent, summarizerAgent]);

        var groupChatAgent = new GroupChatManager(groupChat);

        var history = await userProxyAgent.InitiateChatAsync(
            receiver: groupChatAgent,
            message: "How to deploy an openai resource on azure",
            maxRound: 10);
        #endregion Sequential_GroupChat_Example
    }
}
