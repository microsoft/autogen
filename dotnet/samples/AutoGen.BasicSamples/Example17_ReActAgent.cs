// Copyright (c) Microsoft Corporation. All rights reserved.
// Example17_ReActAgent.cs

using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using OpenAI;
using OpenAI.Chat;

namespace AutoGen.BasicSample;

public class OpenAIReActAgent : IAgent
{
    private readonly ChatClient _client;
    private readonly FunctionContract[] tools;
    private readonly Dictionary<string, Func<string, Task<string>>> toolExecutors = new();
    private readonly IAgent reasoner;
    private readonly IAgent actor;
    private readonly IAgent helper;
    private readonly int maxSteps = 10;

    private const string ReActPrompt = @"Answer the following questions as best you can.
You can invoke the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Tool: the tool to invoke
Tool Input: the input to the tool
Observation: the invoke result of the tool
... (this process can repeat multiple times)

Once you have the final answer, provide the final answer in the following format:
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!
Question: {input}";

    public OpenAIReActAgent(ChatClient client, string name, FunctionContract[] tools, Dictionary<string, Func<string, Task<string>>> toolExecutors)
    {
        _client = client;
        this.Name = name;
        this.tools = tools;
        this.toolExecutors = toolExecutors;
        this.reasoner = CreateReasoner();
        this.actor = CreateActor();
        this.helper = new OpenAIChatAgent(client, "helper")
            .RegisterMessageConnector();
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        // step 1: extract the input question
        var userQuestion = await helper.SendAsync("Extract the question from chat history", chatHistory: messages);
        if (userQuestion.GetContent() is not string question)
        {
            return new TextMessage(Role.Assistant, "I couldn't find a question in the chat history. Please ask a question.", from: Name);
        }
        var reactPrompt = CreateReActPrompt(question);
        var promptMessage = new TextMessage(Role.User, reactPrompt);
        var chatHistory = new List<IMessage>() { promptMessage };

        // step 2: ReAct
        for (int i = 0; i != this.maxSteps; i++)
        {
            // reasoning
            var reasoning = await reasoner.SendAsync(chatHistory: chatHistory);
            if (reasoning.GetContent() is not string reasoningContent)
            {
                return new TextMessage(Role.Assistant, "I couldn't find a reasoning in the chat history. Please provide a reasoning.", from: Name);
            }
            if (reasoningContent.Contains("I now know the final answer"))
            {
                return new TextMessage(Role.Assistant, reasoningContent, from: Name);
            }

            chatHistory.Add(reasoning);

            // action
            var action = await actor.SendAsync(reasoning);
            chatHistory.Add(action);
        }

        // fail to find the final answer
        // return the summary of the chat history
        var summary = await helper.SendAsync("Summarize the chat history and find out what's missing", chatHistory: chatHistory);
        summary.From = Name;

        return summary;
    }

    private string CreateReActPrompt(string input)
    {
        var toolPrompt = tools.Select(t => $"{t.Name}: {t.Description}").Aggregate((a, b) => $"{a}\n{b}");
        var prompt = ReActPrompt.Replace("{tools}", toolPrompt);
        prompt = prompt.Replace("{input}", input);
        return prompt;
    }

    private IAgent CreateReasoner()
    {
        return new OpenAIChatAgent(
            chatClient: _client,
            name: "reasoner")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
    }

    private IAgent CreateActor()
    {
        var functionCallMiddleware = new FunctionCallMiddleware(tools, toolExecutors);
        return new OpenAIChatAgent(
            chatClient: _client,
            name: "actor")
            .RegisterMessageConnector()
            .RegisterMiddleware(functionCallMiddleware)
            .RegisterPrintMessage();
    }
}

public partial class Tools
{
    /// <summary>
    /// Get weather report for a specific place on a specific date
    /// </summary>
    /// <param name="city">city</param>
    /// <param name="date">date as DD/MM/YYYY</param>
    [Function]
    public async Task<string> WeatherReport(string city, string date)
    {
        return $"Weather report for {city} on {date} is sunny";
    }

    /// <summary>
    /// Get current localization
    /// </summary>
    [Function]
    public async Task<string> GetLocalization(string dummy)
    {
        return $"Paris";
    }

    /// <summary>
    /// Get current date as DD/MM/YYYY
    /// </summary>
    [Function]
    public async Task<string> GetDateToday(string dummy)
    {
        return $"27/05/2024";
    }
}

public class Example17_ReActAgent
{
    public static async Task RunAsync()
    {
        var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var modelName = "gpt-4-turbo";
        var tools = new Tools();
        var openAIClient = new OpenAIClient(openAIKey);
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var reactAgent = new OpenAIReActAgent(
            client: openAIClient.GetChatClient(modelName),
            name: "react-agent",
            tools: [tools.GetLocalizationFunctionContract, tools.GetDateTodayFunctionContract, tools.WeatherReportFunctionContract],
            toolExecutors: new Dictionary<string, Func<string, Task<string>>>
            {
                { tools.GetLocalizationFunctionContract.Name, tools.GetLocalizationWrapper },
                { tools.GetDateTodayFunctionContract.Name, tools.GetDateTodayWrapper },
                { tools.WeatherReportFunctionContract.Name, tools.WeatherReportWrapper },
            }
            )
            .RegisterPrintMessage();

        var message = new TextMessage(Role.User, "What is the weather here", from: "user");

        var response = await reactAgent.SendAsync(message);
    }
}
