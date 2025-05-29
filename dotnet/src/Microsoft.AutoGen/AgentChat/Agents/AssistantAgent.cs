// Copyright (c) Microsoft Corporation. All rights reserved.
// AssistantAgent.cs

using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text.Json;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

using ChatMessage = Microsoft.AutoGen.AgentChat.Abstractions.ChatMessage;
using CompletionChatMessage = Microsoft.Extensions.AI.ChatMessage;

namespace Microsoft.AutoGen.AgentChat.Agents;

/// <summary>
/// An agent that provides assistance with tool use.
///
/// The <see cref="HandleAsync(IEnumerable{ChatMessage}, CancellationToken)"/> method returns a
/// <see cref="Response"/> in which the <see cref="Response.Message"/> is the final response
/// message.
///
/// The <see cref="StreamAsync(IEnumerable{ChatMessage}, CancellationToken)"/> creates an async
/// generator that yields inner messages as they are created, and the <see cref="Response"/> object
/// as the last item."/>
///
/// Attention: The caller must only pass new messages to the agent on each call to to the
/// <see cref="HandleAsync(IEnumerable{ChatMessage}, CancellationToken)"/> or the
/// <see cref="StreamAsync(IEnumerable{ChatMessage}, CancellationToken)"/> methods.
/// The agent maintains its state between calls to these methods.
/// Do not pass the entire conversation history to the agent on each call.
///
/// Warning: The agent is not thread or parallel safe. It should not be shared between
/// multiple threads or parallel asynchronous calls, and it should not call its methods
/// concurrently.
///
/// Tool call behavior:
///
/// <list type="bullet">
///   <item>If the model returns no tool call, then the response is immediately returned as a
///   <see cref="TextMessage"/> in the result <see cref="Response.Message"/>.</item>
///   <item>
///     When the model returns tool calls, they will be executed right away.
///     <list type="bullet">
///       <item>
///         When <see cref="ReflectOnToolUse"/> is <c>false</c> (default), the tool calls are
///         returned as a <see cref="ToolCallSummaryMessage"/> in the result <see cref="Response.Message"/>.
///         <see cref="ToolCallSummaryTemplate"/> is used to format the tool call summary, and can
///         be customized on construction."/>
///       </item>
///       <item>
///         When <see cref="ReflectOnToolUse"/> is <c>true</c>, the agent will make another model
///         inference using the tool calls and results, and the text response is returned as a
///         <see cref="TextMessage"/> in the result <see cref="Response.Message"/>.
///       </item>
///     </list>
///   </item>
///   <item>
///     If the model returns multiple tool calls, they will be executed concurrently. To disable
///     parallel tool calls you need to configure the <see cref="IChatClient"/>.
///   </item>
/// </list>
///
/// Tip: By default, the tool call results are returned as response when tool calls are made.
/// So it is recommended to pay attention to the formatting of the tools return values,
/// especially if another agent is expecting them in a specific format.
///
/// Handoff behavior:
///
/// <list type="bullet">
///   <item>
///     If a handoff is triggered, a <see cref="HandoffMessage"/> will be returned in the result
///     <see cref="Response.Message"/>.
///   </item>
///   <item>
///     If there are tool calls, they will be executed right away before returning the handoff.
///   </item>
///   <item>
///     The tool calls and results are passed to the target agent through <see cref="HandoffMessage.Context"/>
///   </item>
/// </list>
///
/// Note: If multiple handoffs are detected, only the first handoff is executed. To avoid this,
/// disable parallel tool calls in the <see cref="IChatClient"/>. configuration.
/// 
/// </summary>
// TODO: Image in the doc
// TODO: Flesh out the Tool Call behaviour section

public class AssistantAgent : ChatAgentBase
{
    private const string DefaultDescription = "An agent that provides assistance with ability to use tools.";
    private const string DefaultSystemPrompt = "You are a helpful AI assistant. Solve tasks using your tools. Reply with 'TERMINATE' when the task has been completed.";
    private const string DefaultToolCallSummaryFormat = "{result}";

    private IChatClient modelClient;

    private CompletionChatMessage? systemMessage;
    private List<CompletionChatMessage> modelContext;

    private ToolManager toolManager;

    /// <summary>
    /// Gets a value indicating whether the agent should reflect on tool use.
    /// </summary>
    public bool ReflectOnToolUse { get; }

    /// <summary>
    /// Gets the tool call summary template.
    /// </summary>
    public PromptTemplate ToolCallSummaryTemplate { get; }

    /// <summary>
    /// Initializes a new instance of the <see cref="AssistantAgent"/> class.
    /// </summary>
    /// <param name="name">The name of the agent.</param>
    /// <param name="modelClient">The model client to use for inference.</param>
    /// <param name="description">The description of the agent.</param>
    /// <param name="systemPrompt"></param>
    /// <param name="tools">The tools to register with the agent.</param>
    /// <param name="handoffs">The handoff configurations for the agent.</param>
    /// <param name="reflectOnToolUse">
    /// If <c>true</c>, the agent will make another model inference using the tool call and result
    /// to generate a response. If <c>false</c>, the tool call result will be returned as the response.
    /// Defaults to <c>false</c>.
    /// </param>
    /// <param name="toolCallSummaryFormat">
    /// The format string used to create a tool call summary for every tool call result. Defaults to
    /// "{result}".
    /// </param>
    /// <exception cref="ArgumentException">
    /// Thrown when a tool or handoff name is not unique (including when a handoff name is the same as a tool name).
    /// </exception>
    public AssistantAgent(string name,
                          IChatClient modelClient,
                          string description = DefaultDescription,
                          string? systemPrompt = DefaultSystemPrompt,
                          IEnumerable<ITool>? tools = null,
                          IEnumerable<Handoff>? handoffs = null,
                          bool reflectOnToolUse = false,
                          string toolCallSummaryFormat = DefaultToolCallSummaryFormat)
        : base(name, description)
    {
        this.modelClient = modelClient;

        if (systemPrompt != null)
        {
            this.systemMessage = new CompletionChatMessage(ChatRole.System, systemPrompt);
            this.modelContext = [this.systemMessage];
        }
        else
        {
            this.systemMessage = null;
            this.modelContext = [];
        }

        this.toolManager = new ToolManager(tools ?? [], handoffs ?? []);

        this.ReflectOnToolUse = reflectOnToolUse;

        // TODO: Python does not validate - should we do so here? If so, what should the validation
        // rules be? (Presumably we should not allow any template arguments besides {result}, {tool_name}, {arguments}
        this.ToolCallSummaryTemplate = new PromptTemplate(toolCallSummaryFormat);
    }

    /// <inheritdoc cref="IChatAgent.ProducedMessageTypes"/>
    public override IEnumerable<Type> ProducedMessageTypes
    {
        get
        {
            IEnumerable<Type> messages = [typeof(TextMessage)];

            if (this.toolManager.Handoffs.Any())
            {
                messages = messages.Concat([typeof(HandoffMessage)]);
            }

            if (this.toolManager.Tools.Any())
            {
                messages = messages.Concat([typeof(ToolCallSummaryMessage)]);
            }

            return messages;
        }
    }

    private IDictionary<string, ITool> Tools => this.toolManager.Tools;

    /// <inheritdoc cref="ChatAgentBase.HandleAsync"/>
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

    private static FunctionCall ToAgentCall(FunctionCallContent functionCall)
    {
        string? argumentsJson = null;
        if (functionCall.Arguments?.Count > 0)
        {
            argumentsJson = JsonSerializer.Serialize(functionCall.Arguments);
        }

        return new FunctionCall
        {
            Id = functionCall.CallId,
            Name = functionCall.Name,
            Arguments = argumentsJson
        };
    }

    private static ToolCallRequestEvent ToAgentEvent(IList<FunctionCallContent> calls, string source)
    {
        ToolCallRequestEvent result = new ToolCallRequestEvent()
        {
            Source = source
        };

        result.Content.AddRange(calls.Select(ToAgentCall));

        return result;
    }

    private static FunctionExecutionResult ToAgentResult(FunctionResultContent result)
    {
        return new FunctionExecutionResult
        {
            Id = result.CallId,
            Content = JsonSerializer.Serialize(result.Result),
        };
    }

    private static ToolCallExecutionEvent ToAgentEvent(IList<FunctionResultContent> results, string source)
    {
        ToolCallExecutionEvent result = new ToolCallExecutionEvent()
        {
            Source = source
        };
        result.Content.AddRange(results.Select(ToAgentResult));
        return result;
    }

    /// <inheritdoc cref="ChatAgentBase.StreamAsync"/>
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
            Tools = (from tool in this.Tools.Values select (AITool)tool.AIFunction).ToList()
        };

        ChatCompletion completion = await this.modelClient.CompleteAsync(this.modelContext, options, cancellationToken);

        // TODO: Flatten traverses the message contents already; we are about to do it again: There's a better way.
        this.modelContext.Add(completion.Message.Flatten());

        // TODO: I am not sure this is doing what we want it to be doing: This checks that everything inside of the
        // completion is a FunctionCall.

        while (completion.Message.Contents.All(content => content is FunctionCallContent))
        {
            // TODO: A nicer API for this
            List<FunctionCallContent> calls = completion.Message.Contents.Cast<FunctionCallContent>().ToList();

            yield return new ChatStreamFrame
            {
                Type = ChatStreamFrame.FrameType.InternalMessage,
                InternalMessage = ToAgentEvent(calls, this.Name)
            };

            List<Task<FunctionResultContent>> toolCallTasks = (from call in calls
                                                               select this.toolManager.InvokeToolAsync(call, cancellationToken))
                                                              .ToList();

            // TODO: Enable streaming the results as they come in, rather than in a batch?
            FunctionResultContent[] taskResult = await Task.WhenAll(toolCallTasks);
            ToolCallExecutionEvent toolCallResult = ToAgentEvent(taskResult, this.Name);

            this.modelContext.Add(toolCallResult.ToCompletionClientMessage());

            yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.InternalMessage, InternalMessage = toolCallResult };

            List<Handoff> handoffs = (from FunctionResultContent result in taskResult
                                      where this.toolManager.Handoffs.Contains(result.Name)
                                      select (Handoff)this.toolManager.Tools[result.Name])
                                     .ToList();

            if (handoffs.Count > 1)
            {
                throw new InvalidOperationException($"Multiple handoffs detected: {String.Join(", ", from handoff in handoffs select handoff.Name)}");
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
                            Context = handoffs[0].Message
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

    /// <inheritdoc cref="IChatAgent.ResetAsync"/>
    public override ValueTask ResetAsync(CancellationToken cancellationToken)
    {
        this.modelContext = [this.systemMessage];
        return ValueTask.CompletedTask;
    }
}
