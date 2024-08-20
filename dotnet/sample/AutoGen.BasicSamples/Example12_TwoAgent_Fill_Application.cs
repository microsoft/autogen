// Copyright (c) Microsoft Corporation. All rights reserved.
// Example12_TwoAgent_Fill_Application.cs

using System.Text;
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;

namespace AutoGen.BasicSample;

public partial class TwoAgent_Fill_Application
{
    private string? name = null;
    private string? email = null;
    private string? phone = null;
    private string? address = null;
    private bool? receiveUpdates = null;

    [Function]
    public async Task<string> SaveProgress(
        string name,
        string email,
        string phone,
        string address,
        bool? receiveUpdates)
    {
        this.name = !string.IsNullOrEmpty(name) ? name : this.name;
        this.email = !string.IsNullOrEmpty(email) ? email : this.email;
        this.phone = !string.IsNullOrEmpty(phone) ? phone : this.phone;
        this.address = !string.IsNullOrEmpty(address) ? address : this.address;
        this.receiveUpdates = receiveUpdates ?? this.receiveUpdates;

        var missingInformationStringBuilder = new StringBuilder();
        if (string.IsNullOrEmpty(this.name))
        {
            missingInformationStringBuilder.AppendLine("Name is missing.");
        }

        if (string.IsNullOrEmpty(this.email))
        {
            missingInformationStringBuilder.AppendLine("Email is missing.");
        }

        if (string.IsNullOrEmpty(this.phone))
        {
            missingInformationStringBuilder.AppendLine("Phone is missing.");
        }

        if (string.IsNullOrEmpty(this.address))
        {
            missingInformationStringBuilder.AppendLine("Address is missing.");
        }

        if (this.receiveUpdates == null)
        {
            missingInformationStringBuilder.AppendLine("ReceiveUpdates is missing.");
        }

        if (missingInformationStringBuilder.Length > 0)
        {
            return missingInformationStringBuilder.ToString();
        }
        else
        {
            return "Application information is saved to database.";
        }
    }

    public static async Task<IAgent> CreateSaveProgressAgent()
    {
        var gpt3Config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endPoint = gpt3Config.Endpoint ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var apiKey = gpt3Config.ApiKey ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var openaiClient = new OpenAIClient(new Uri(endPoint), new Azure.AzureKeyCredential(apiKey));

        var instance = new TwoAgent_Fill_Application();
        var functionCallConnector = new FunctionCallMiddleware(
            functions: [instance.SaveProgressFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { instance.SaveProgressFunctionContract.Name, instance.SaveProgressWrapper },
            });

        var chatAgent = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "application",
            modelName: gpt3Config.DeploymentName,
            systemMessage: """You are a helpful application form assistant who saves progress while user fills application.""")
            .RegisterMessageConnector()
            .RegisterMiddleware(functionCallConnector)
            .RegisterMiddleware(async (msgs, option, agent, ct) =>
            {
                var lastUserMessage = msgs.Last() ?? throw new Exception("No user message found.");
                var prompt = $"""
                Save progress according to the most recent information provided by user.

                ```user
                {lastUserMessage.GetContent()}
                ```
                """;

                return await agent.GenerateReplyAsync([lastUserMessage], option, ct);

            });

        return chatAgent;
    }

    public static async Task<IAgent> CreateAssistantAgent()
    {
        var gpt3Config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endPoint = gpt3Config.Endpoint ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var apiKey = gpt3Config.ApiKey ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var openaiClient = new OpenAIClient(new Uri(endPoint), new Azure.AzureKeyCredential(apiKey));

        var chatAgent = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "assistant",
            modelName: gpt3Config.DeploymentName,
            systemMessage: """You create polite prompt to ask user provide missing information""")
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        return chatAgent;
    }

    public static async Task<IAgent> CreateUserAgent()
    {
        var gpt3Config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endPoint = gpt3Config.Endpoint ?? throw new Exception("Please set AZURE_OPENAI_ENDPOINT environment variable.");
        var apiKey = gpt3Config.ApiKey ?? throw new Exception("Please set AZURE_OPENAI_API_KEY environment variable.");
        var openaiClient = new OpenAIClient(new Uri(endPoint), new Azure.AzureKeyCredential(apiKey));

        var chatAgent = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "user",
            modelName: gpt3Config.DeploymentName,
            systemMessage: """
            You are a user who is filling an application form. Simply provide the information as requested and answer the questions, don't do anything else.
            
            here's some personal information about you:
            - name: John Doe
            - email: 1234567@gmail.com
            - phone: 123-456-7890
            - address: 1234 Main St, Redmond, WA 98052
            - want to receive update? true
            """)
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        return chatAgent;
    }

    public static async Task RunAsync()
    {
        var applicationAgent = await CreateSaveProgressAgent();
        var assistantAgent = await CreateAssistantAgent();
        var userAgent = await CreateUserAgent();

        var userToApplicationTransition = Transition.Create(userAgent, applicationAgent);
        var applicationToAssistantTransition = Transition.Create(applicationAgent, assistantAgent);
        var assistantToUserTransition = Transition.Create(assistantAgent, userAgent);

        var workflow = new Graph(
            [
                userToApplicationTransition,
                applicationToAssistantTransition,
                assistantToUserTransition,
            ]);

        var groupChat = new GroupChat(
            members: [userAgent, applicationAgent, assistantAgent],
            workflow: workflow);

        var groupChatManager = new GroupChatManager(groupChat);
        var initialMessage = await assistantAgent.SendAsync("Generate a greeting meesage for user and start the conversation by asking what's their name.");

        var chatHistory = new List<IMessage> { initialMessage };
        await foreach (var msg in userAgent.SendAsync(groupChatManager, chatHistory, maxRound: 30))
        {
            if (msg.GetContent().ToLower().Contains("application information is saved to database.") is true)
            {
                break;
            }
        }
    }
}
