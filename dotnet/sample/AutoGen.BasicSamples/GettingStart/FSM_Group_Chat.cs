// Copyright (c) Microsoft Corporation. All rights reserved.
// FSM_Group_Chat.cs

using System.Text;
#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;
#endregion Using

namespace AutoGen.BasicSample;

#region FillFormTool
public partial class FillFormTool
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
}
#endregion FillFormTool

public class FSM_Group_Chat
{
    public static async Task<IAgent> CreateSaveProgressAgent(OpenAIClient client, string model)
    {
        #region Create_Save_Progress_Agent
        var tool = new FillFormTool();
        var functionCallMiddleware = new FunctionCallMiddleware(
            functions: [tool.SaveProgressFunctionContract],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { tool.SaveProgressFunctionContract.Name!, tool.SaveProgressWrapper },
            });

        var chatAgent = new OpenAIChatAgent(
            openAIClient: client,
            name: "application",
            modelName: model,
            systemMessage: """You are a helpful application form assistant who saves progress while user fills application.""")
            .RegisterMessageConnector()
            .RegisterMiddleware(functionCallMiddleware)
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
        #endregion Create_Save_Progress_Agent

        return chatAgent;
    }

    public static async Task<IAgent> CreateAssistantAgent(OpenAIClient openaiClient, string model)
    {
        #region Create_Assistant_Agent
        var chatAgent = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "assistant",
            modelName: model,
            systemMessage: """You create polite prompt to ask user provide missing information""")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Assistant_Agent
        return chatAgent;
    }

    public static async Task<IAgent> CreateUserAgent(OpenAIClient openaiClient, string model)
    {
        #region Create_User_Agent
        var chatAgent = new OpenAIChatAgent(
            openAIClient: openaiClient,
            name: "user",
            modelName: model,
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
        #endregion Create_User_Agent
        return chatAgent;
    }

    public static async Task RunAsync()
    {
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var model = "gpt-3.5-turbo";
        var openaiClient = new OpenAIClient(apiKey);
        var applicationAgent = await CreateSaveProgressAgent(openaiClient, model);
        var assistantAgent = await CreateAssistantAgent(openaiClient, model);
        var userAgent = await CreateUserAgent(openaiClient, model);

        #region Create_Graph
        var userToApplicationTransition = Transition.Create(userAgent, applicationAgent);
        var applicationToAssistantTransition = Transition.Create(applicationAgent, assistantAgent);
        var assistantToUserTransition = Transition.Create(assistantAgent, userAgent);

        var workflow = new Graph(
            [
                userToApplicationTransition,
                applicationToAssistantTransition,
                assistantToUserTransition,
            ]);
        #endregion Create_Graph

        #region Group_Chat
        var groupChat = new GroupChat(
            members: [userAgent, applicationAgent, assistantAgent],
            workflow: workflow);
        #endregion Group_Chat

        var initialMessage = await assistantAgent.SendAsync("Generate a greeting meesage for user and start the conversation by asking what's their name.");

        var chatHistory = new List<IMessage> { initialMessage };
        await foreach (var msg in groupChat.SendAsync(chatHistory, maxRound: 30))
        {
            if (msg.GetContent().ToLower().Contains("application information is saved to database.") is true)
            {
                break;
            }
        }
    }
}
