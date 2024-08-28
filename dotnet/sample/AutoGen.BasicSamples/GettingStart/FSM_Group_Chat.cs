// Copyright (c) Microsoft Corporation. All rights reserved.
// FSM_Group_Chat.cs

using System.Text;
#region Using
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using OpenAI;
using OpenAI.Chat;
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
    public static async Task<IAgent> CreateSaveProgressAgent(ChatClient client)
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
            chatClient: client,
            name: "application",
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

    public static async Task<IAgent> CreateAssistantAgent(ChatClient chatClient)
    {
        #region Create_Assistant_Agent
        var chatAgent = new OpenAIChatAgent(
            chatClient: chatClient,
            name: "assistant",
            systemMessage: """You create polite prompt to ask user provide missing information""")
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion Create_Assistant_Agent
        return chatAgent;
    }

    public static async Task<IAgent> CreateUserAgent(ChatClient chatClient)
    {
        #region Create_User_Agent
        var chatAgent = new OpenAIChatAgent(
            chatClient: chatClient,
            name: "user",
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
        var model = "gpt-4o-mini";
        var openaiClient = new OpenAIClient(apiKey);
        var chatClient = openaiClient.GetChatClient(model);
        var applicationAgent = await CreateSaveProgressAgent(chatClient);
        var assistantAgent = await CreateAssistantAgent(chatClient);
        var userAgent = await CreateUserAgent(chatClient);

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
