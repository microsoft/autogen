// Copyright (c) Microsoft Corporation. All rights reserved.
// CodingAssistantAgent.cs

using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

using ChatMessage = Microsoft.AutoGen.AgentChat.Abstractions.ChatMessage;
using CompletionChatMessage = Microsoft.Extensions.AI.ChatMessage;

namespace Microsoft.AutoGen.AgentChat.Agents;

// TODO: Replatfrom this on top of AssistantAgent
public class CodingAssistantAgent : ChatAgentBase
{
    // TODO: How do we make this be more pluggable depending on what ICodeExecutor can expect to be able to code?
    private const string DefaultDescription = "A helpful and general-purpose AI assistant that has strong language skills, Python skills, and C# .NET skills.";
    private const string DefaultPrompt = @"You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply ""TERMINATE"" in the end when code has been executed and task is complete.";

    //private string prompt;
    private IChatClient completionClient;

    private CompletionChatMessage systemMessage;
    private List<CompletionChatMessage> modelContext;

    public CodingAssistantAgent(string name, IChatClient completionClient, string description = DefaultDescription, string prompt = DefaultPrompt) : base(name, description)
    {
        this.completionClient = completionClient;
        //this.prompt = prompt;

        systemMessage = new CompletionChatMessage(ChatRole.System, prompt);
        modelContext = new List<CompletionChatMessage>();

        // TODO: More coherent defaults for ChatOptions? Is this even needed?
        ChatOptions = null;
    }

    public ChatOptions? ChatOptions { get; set; }

    public override IEnumerable<Type> ProducedMessageTypes => [typeof(TextMessage)];

    public override async ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> messages, CancellationToken cancellationToken)
    {
        foreach (var message in messages)
        {
            CompletionChatMessage completionMessage;
            if (message is TextMessage textMessage)
            {
                completionMessage = new CompletionChatMessage(ChatRole.User, textMessage.Content);
            }
            else if (message is MultiModalMessage multiModalMessage)
            {
                // TODO: Microsoft.Abstractions.AI.MultiModalMessage is not implemented
                completionMessage = new CompletionChatMessage(ChatRole.User, multiModalMessage);
            }
            else if (message is StopMessage stopMessage)
            {
                completionMessage = new CompletionChatMessage(ChatRole.User, stopMessage.Content);
            }
            else
            {
                throw new ArgumentException($"Unsupported message type: {message.GetType()}");
            }

            modelContext.Add(completionMessage);
        }

        var llmMessages = new List<CompletionChatMessage>();
        llmMessages.Add(systemMessage);
        llmMessages.AddRange(modelContext);

        var completion = await completionClient.CompleteAsync(llmMessages, ChatOptions, cancellationToken);

        // TODO: Do a more reasonable thing here when there are multiple choices?
        var choice = completion.Choices[0];
        var result = new MultiModalMessage() { Source = Name };

        foreach (var item in choice.Contents)
        {
            result.Add(item);
        }

        return new Response { Message = result };
    }

    public override ValueTask ResetAsync(CancellationToken cancellationToken)
    {
        return ValueTask.CompletedTask;
    }
}
