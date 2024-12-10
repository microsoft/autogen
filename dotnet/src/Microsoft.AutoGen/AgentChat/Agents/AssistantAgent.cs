// Copyright (c) Microsoft Corporation. All rights reserved.
// AssistantAgent.cs

using System.Diagnostics;
using System.Runtime.CompilerServices;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

using ChatMessage = Microsoft.AutoGen.AgentChat.Abstractions.ChatMessage;
using CompletionChatMessage = Microsoft.Extensions.AI.ChatMessage;

namespace Microsoft.AutoGen.AgentChat.Agents;

public class AssistantAgent : ChatAgentBase
{
    private const string DefaultDescription = "An agent that provides assistance with ability to use tools.";
    private const string DefaultSystemPrompt = "You are a helpful AI assistant. Solve tasks using your tools. Reply with 'TERMINATE' when the task has been completed.";

    private IChatClient modelClient;

    private Dictionary<string, ITool> tools;

    private CompletionChatMessage systemMessage;
    private List<CompletionChatMessage> modelContext;

    private HashSet<string> handoffs;

    private static Dictionary<string, ITool> PrepareTools(IEnumerable<ITool>? tools, IEnumerable<Handoff>? handoffs, out HashSet<string> handoffNames)
    {
        Dictionary<string, ITool> result = new Dictionary<string, ITool>();
        handoffNames = [];

        foreach (ITool tool in tools ?? [])
        {
            if (result.ContainsKey(tool.Name))
            {
                throw new ArgumentException($"Tool names must be unique. Duplicate tool name: {tool.Name}");
            }

            result[tool.Name] = tool;
        }

        foreach (Handoff handoff in handoffs ?? [])
        {
            if (handoffNames.Contains(handoff.Name))
            {
                throw new ArgumentException($"Handoff names must be unique. Duplicate handoff name: {handoff.Name}");
            }

            if (result.ContainsKey(handoff.Name))
            {
                throw new ArgumentException($"Handoff names must be unique from tool names. Duplicate handoff name: {handoff.Name}");
            }

            result[handoff.Name] = handoff.HandoffTool;
            handoffNames.Add(handoff.Name);
        }

        return result;
    }

    private static Dictionary<string, Handoff> PrepareHandoffs(IEnumerable<Handoff>? handoffs, HashSet<string> uniqueToolNames, out List<ITool> handoffTools)
    {
        if (handoffs == null)
        {
            handoffTools = [];
            return new Dictionary<string, Handoff>();
        }

        HashSet<string> uniqueNames = new HashSet<string>(from handoff in handoffs select handoff.Name);
        if (uniqueNames.Count != handoffs.Count())
        {
            throw new ArgumentException($"Handoff names must be unique.");
        }

        if (uniqueNames.Overlaps(uniqueToolNames))
        {
            throw new ArgumentException("Handoff names must be unique from tool names.");
        }

        handoffTools = (from handoff in handoffs select handoff.HandoffTool).ToList();
        return handoffs.ToDictionary(handoff => handoff.Name);
    }

    public AssistantAgent(string name,
                          IChatClient modelClient,
                          string description = DefaultDescription,
                          string systemPrompt = DefaultSystemPrompt,
                          IEnumerable<ITool>? tools = null,
                          IEnumerable<Handoff>? handoffs = null)
        : base(name, description)
    {
        this.modelClient = modelClient;
        this.systemMessage = new CompletionChatMessage(ChatRole.System, systemPrompt);
        this.modelContext = [this.systemMessage];

        this.tools = AssistantAgent.PrepareTools(tools, handoffs, out this.handoffs);
    }

    public override IEnumerable<Type> ProducedMessageTypes =>
        this.handoffs.Any() ? [typeof(TextMessage), typeof(HandoffMessage)]
                            : [typeof(TextMessage)];

    public override async ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> item, CancellationToken cancellationToken)
    {
        await foreach (ChatStreamFrame frame in this.StreamAsync(item, cancellationToken))
        {
            if (frame.Type == ChatStreamFrame.FrameType.Response)
            {
                return frame.Response!;
            }
        }

        throw new InvalidOperationException("The stream should have returned a final result.");
    }

    private async Task<FunctionResultContent> InvokeToolAsync(FunctionCallContent functionCall, CancellationToken cancellationToken)
    {
        if (this.tools.Count == 0)
        {
            throw new InvalidOperationException("No tools available.");
        }

        ITool? targetTool = this.tools.GetValueOrDefault(functionCall.Name)
                            ?? throw new ArgumentException($"Unknown tool: {functionCall.Name}");

        List<object?> parameters = new List<object?>();
        if (functionCall.Arguments != null)
        {
            foreach (var parameter in targetTool.Parameters)
            {
                if (!functionCall.Arguments!.TryGetValue(parameter.Name, out object? o))
                {
                    if (parameter.IsRequired)
                    {
                        throw new ArgumentException($"Missing required parameter: {parameter.Name}");
                    }
                    else
                    {
                        o = parameter.DefaultValue;
                    }
                }

                parameters.Add(o);
            }
        }

        try
        {
            // TODO: Nullability constraint on the tool execution is bad
            object callResult = await targetTool.ExecuteAsync((IEnumerable<object>)parameters, cancellationToken);

            return new FunctionResultContent(functionCall.CallId, functionCall.Name, callResult);
        }
        catch (Exception e)
        {
            return new FunctionResultContent(functionCall.CallId, functionCall.Name, $"Error: {e}");
        }
    }

    public override async IAsyncEnumerable<ChatStreamFrame> StreamAsync(IEnumerable<ChatMessage> item, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        // TODO: feed the right Roles into the call
        this.modelContext.AddRange(from message in item select message.ToCompletionClientMessage(ChatRole.User));

        List<AgentMessage> innerMessages = [];

        ChatOptions options = new()
        {
            ToolMode = ChatToolMode.Auto,

            // TODO: We should probably just use the M.E.Ai.Abtraction types directly
            // TODO: Should we cache this List? Also, why is this a list, rather than an Enumerable?
            Tools = (from tool in this.tools.Values select (AITool)tool.AIFunction).ToList()
        };

        ChatCompletion completion = await this.modelClient.CompleteAsync(this.modelContext, options, cancellationToken);

        // TODO: Flatten traverses the message contents already; we are about to do it again: There's a better way.
        this.modelContext.Add(completion.Message.Flatten());

        // TODO: I am not sure this is doing what we want it to be doing: This checks that everything inside of the
        // completion is a FunctionCall.

        while (completion.Message.Contents.All(content => content is FunctionCallContent))
        {
            ToolCallMessage toolCall = new() { Source = this.Name };

            // TODO: A nicer API for this
            IEnumerable<FunctionCallContent> calls = completion.Message.Contents.Cast<FunctionCallContent>();
            toolCall.Content.AddRange(calls);

            yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.InternalMessage, InternalMessage = toolCall };

            List<Task<FunctionResultContent>> toolCallTasks = (from call in calls
                                                               select InvokeToolAsync(call, cancellationToken))
                                                              .ToList();

            // TODO: Enable streaming the results as they come in, rather than in a batch?
            FunctionResultContent[] taskResult = await Task.WhenAll(toolCallTasks);
            ToolCallResultMessage toolCallResult = new() { Source = this.Name };
            toolCallResult.Content.AddRange(taskResult);

            this.modelContext.Add(toolCallResult.ToCompletionClientMessage());

            yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.InternalMessage, InternalMessage = toolCallResult };

            List<Handoff> handoffs = (from FunctionResultContent result in taskResult
                                      where this.handoffs.Contains(result.Name)
                                      select (Handoff)this.tools[result.Name])
                                     .ToList();

            if (handoffs.Count > 1)
            {
                throw new InvalidOperationException($"Multiple handoffs detected: { String.Join(", ", from handoff in handoffs select handoff.Name) }");
            }
            else if (handoffs.Count == 1)
            {
                yield return new ChatStreamFrame
                             {
                                 Type = ChatStreamFrame.FrameType.Response,
                                 Response = new Response
                                 {
                                     Message = new HandoffMessage
                                     {
                                         Source = this.Name,
                                         Target = handoffs[0].Target,
                                         Content = handoffs[0].Message
                                     }
                                 }
                             };
                yield break;
            }

            completion = await this.modelClient.CompleteAsync(this.modelContext, options, cancellationToken);
            this.modelContext.Add(completion.Message.Flatten());
        }

        // We expect the completion to be a single TextContent at this point
        Debug.Assert(completion.Message.Contents.Count != 1 || !(completion.Message.Contents[0] is TextContent));
        yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.Response, Response = new Response { Message = new TextMessage { Source = this.Name, Content = completion.Message.Text! } } };
    }

    public override ValueTask ResetAsync(CancellationToken cancellationToken)
    {
        this.modelContext = [this.systemMessage];
        return ValueTask.CompletedTask;
    }
}
