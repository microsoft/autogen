// Copyright (c) Microsoft Corporation. All rights reserved.
// SocietyOfMindAgent.cs

using System.Runtime.CompilerServices;
using System.Text;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

using ChatMessage = Microsoft.AutoGen.AgentChat.Abstractions.ChatMessage;
using MEAI = Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Agents;

[InterpolatedStringHandler]
public class TemplateBuilder
{
    private readonly List<StringTemplate.Run> segments = [];
    private StringTemplate.LiteralRun? currentLiteralRun = new StringTemplate.LiteralRun();

    public TemplateBuilder(int literalLength, int formattedCount)
    {
    }

    public void AppendLiteral(string literal)
    {
        (this.currentLiteralRun ??= new StringTemplate.LiteralRun()).Append(literal);
    }

    public void AppendFormatted<T>(T value, string? format = null)
    {
        if (value is StringTemplate.Slot slot)
        {
            if (this.currentLiteralRun != null)
            {
                this.segments.Add(this.currentLiteralRun);
                this.currentLiteralRun = null;
            }

            this.segments.Add(slot.BindFormat(format));
        }
        else
        {
            this.AppendLiteral(string.Format($"{{0:{format}}}", value));
        }
    }

    public StringBuilder BuildTo(StringBuilder target, IDictionary<string, object?> values)
    {
        if (this.currentLiteralRun != null)
        {
            this.segments.Add(this.currentLiteralRun);
            this.currentLiteralRun = null;
        }

        foreach (var segment in this.segments)
        {
            segment.BuildTo(target, values);
        }

        return target;
    }

    public string Build(IDictionary<string, object?> values)
    {
        return this.BuildTo(new StringBuilder(), values).ToString();
    }
}

public class StringTemplate(TemplateBuilder builder)
{
    public record struct Slot(string Name)
    {
        internal SlotFormatter BindFormat(string? format) => new SlotFormatter(Name, format);
    }

    internal sealed record class SlotFormatter(string Name, string? Format)
    {
        private string FormatInternal<T>(T value)
        {
            // If value is null, but the format string is not, return an empty string.
            if (value == null)
            {
                return string.Empty;
            }

            return Format == null ? value.ToString() ?? string.Empty : string.Format(Format, value);
        }

        private StringBuilder AppendInternal<T>(StringBuilder target, T value)
        {
            return Format == null ? target.Append(value) : target.AppendFormat($"{{0:{Format}}}", value);
        }

        public string FormatString<T>(T value) => FormatInternal(value);
        public string FormatString(IDictionary<string, object> values) => FormatInternal(values[Name]);

        public StringBuilder AppendFormatted<T>(StringBuilder target, T value) => AppendInternal(target, value);
        public StringBuilder AppendFormatted(StringBuilder target, IDictionary<string, object?> values) => AppendInternal(target, values[Name]);
    }

    internal sealed class LiteralRun
    {
        private readonly List<string> literals = [];

        public void Append(string literal)
        {
            if (string.IsNullOrEmpty(literal))
            {
                return;
            }

            this.literals.Add(literal);
        }

        public string Build(bool memoize = true)
        {
            switch (this.literals.Count)
            {
                case 0:
                    return string.Empty;
                case 1:
                    return this.literals[0];
                default:
                    string result = string.Concat(this.literals);

                    if (memoize)
                    {
                        this.literals.Clear();
                        this.literals.Add(result);
                    }

                    return result;
            }
        }

        public StringBuilder BuildTo(StringBuilder target)
        {
            switch (this.literals.Count)
            {
                case 0:
                    return target;
                case 1:
                    return target.Append(this.literals[0]);
                // TODO: Manually unroll small counts?
                default:
                    return literals.Aggregate(target, (t, s) => t.Append(s));
            }
        }
    }

    internal struct Run
    {
        public bool IsLiteral { get; }

        public LiteralRun? Literal { get; }
        public SlotFormatter? DynamicSlot { get; }

        public Run(LiteralRun literal)
        {
            this.IsLiteral = true;
            this.Literal = literal;
            this.DynamicSlot = null;
        }

        public Run(SlotFormatter slot)
        {
            this.IsLiteral = false;
            this.Literal = null;
            this.DynamicSlot = slot;
        }

        public static implicit operator Run(LiteralRun literal) => new Run(literal);
        public static implicit operator Run(SlotFormatter slot) => new Run(slot);

        public StringBuilder BuildTo(StringBuilder target, IDictionary<string, object?> values)
        {
            if (this.IsLiteral)
            {
                return this.Literal!.BuildTo(target);
            }
            else
            {
                return this.DynamicSlot!.AppendFormatted(target, values);
            }
        }
    }

    private TemplateBuilder templateBuilder = builder;

    public StringBuilder BuildTo(StringBuilder target, IDictionary<string, object?> values)
    {
        return this.templateBuilder.BuildTo(target, values);
    }

    public string Build(IDictionary<string, object?> values)
    {
        return this.templateBuilder.Build(values);
    }
}

public class SocietyOfMindAgent : ChatAgentBase
{
    public static readonly StringTemplate.Slot TranscriptSlot = new StringTemplate.Slot("transcript");

    public const string DefaultDescription = "";
    public readonly StringTemplate DefaultTaskPrompt = new($"{TranscriptSlot}\nContinue.");
    public readonly StringTemplate DefaultResponsePrompt = new($"Here is a transcript of conversation so far:\n{TranscriptSlot}\n\\Provide a response to the original request.");

    private ITeam team;
    private IChatClient chatClient;

    private StringTemplate taskPrompt;
    private StringTemplate responsePrompt;

    public SocietyOfMindAgent(string name, ITeam team, IChatClient chatClient, string description = DefaultDescription, StringTemplate? taskPrompt = null, StringTemplate? responsePrompt = null)
        : base(name, description)
    {
        this.team = team;
        this.chatClient = chatClient;

        this.taskPrompt = taskPrompt ?? this.DefaultTaskPrompt;
        this.responsePrompt = responsePrompt ?? this.DefaultResponsePrompt;
    }

    private string FormatTask(StringBuilder transcript)
    {
        return this.taskPrompt.Build(new Dictionary<string, object?> { ["transcript"] = transcript });
    }

    private string FormatResponse(StringBuilder transcript)
    {
        return this.responsePrompt.Build(new Dictionary<string, object?> { ["transcript"] = transcript });
    }

    public override IEnumerable<Type> ProducedMessageTypes => [];

    private StringBuilder CreateTranscript(IEnumerable<AgentMessage> item)
    {
        StringBuilder transcript = new StringBuilder();

        // TODO: It is unclear how to deal with tool use messages here (Python deals with duck typing better)
        foreach (ChatMessage message in item.OfType<ChatMessage>())
        {
            _ = message switch
            {
                TextMessage textMessage => transcript.AppendLine($"{message.Source}: {textMessage.Content}"),
                StopMessage stopMessage => transcript.AppendLine($"{message.Source}: {stopMessage.Content}"),
                HandoffMessage handoffMessage => transcript.AppendLine($"{message.Source}: {handoffMessage.Context}"),

                MultiModalMessage multiModalMessage => AppendMultiModalMessage(multiModalMessage),
                _ => throw new InvalidOperationException($"Unexpected message type: {message} in {this.GetType().FullName}"),
            };
        }

        return transcript;

        StringBuilder AppendMultiModalMessage(MultiModalMessage message)
        {
            foreach (MultiModalData part in message.Content)
            {
                transcript.Append($"{message.Source}: ");

                if (part.ContentType == MultiModalData.Type.String)
                {
                    transcript.AppendLine(((TextContent)part.AIContent).Text);
                }
                else if (part.ContentType == MultiModalData.Type.Image)
                {
                    transcript.AppendLine("[Image]");
                }
                else
                {
                    // Best efforts
                    transcript.AppendLine(part.AIContent.RawRepresentation?.ToString() ?? part.AIContent.ToString());
                }
            }

            return transcript;
        }
    }

    private ChatStreamFrame ProduceResponse(string result)
    {
        Response response = new Response { Message = new TextMessage { Source = this.Name, Content = result } };
        return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.Response, Response = response };
    }

    public override async ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> item, CancellationToken cancellationToken)
    {
        // In the Python implementation AssistantAgent and SocietyOfMindAgent have different strategies for
        // reducing on_messages to on_messages_stream. The former returns the first Response as the final
        // result, while the latter takes the last
        Response? response = null;
        await foreach (ChatStreamFrame frame in this.StreamAsync(item, cancellationToken))
        {
            if (frame.Type == ChatStreamFrame.FrameType.Response)
            {
                response = frame.Response;
            }
        }

        return response ?? throw new InvalidOperationException("No response.");
    }

    public override async IAsyncEnumerable<ChatStreamFrame> StreamAsync(IEnumerable<ChatMessage> item, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        List<ChatMessage> delta = item.ToList();
        string taskSpecification = this.FormatTask(this.CreateTranscript(delta));

        TaskResult? result = null;
        List<AgentMessage> innerMessages = [];

        await foreach (TaskFrame frame in this.team.StreamAsync(taskSpecification, cancellationToken))
        {
            if (frame.Type == TaskFrame.FrameType.Response)
            {
                result = frame.Response!;
                //break; // Python does not break out on receiving a response, so last response wins
            }
            else // if (frame.Type == StreamingFrame<TaskResult>.FrameType.InternalMessage)
            {
                yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.InternalMessage, InternalMessage = frame.InternalMessage! };
                innerMessages.Add(frame.InternalMessage!);
            }
        }

        if (result == null)
        {
            throw new InvalidOperationException("The team did not produce a final response. Check the team's RunAsync method.");
        }

        // The first message is the task message, so we need at least two messages
        if (innerMessages.Count < 2)
        {
            yield return this.ProduceResponse("No response.");
        }
        else
        {
            string prompt = this.FormatResponse(this.CreateTranscript(innerMessages.Skip(1)));

            List<MEAI.ChatMessage> messages = [new MEAI.ChatMessage(ChatRole.System, prompt)];

            ChatCompletion completion = await this.chatClient.CompleteAsync(messages);
            if (completion.Choices.Count < 1 ||
                completion.Choices[0].Text == null)
            {
                throw new InvalidOperationException("Could not produce final result.");
            }

            yield return this.ProduceResponse(completion.Choices[0].Text!);
        }

        await this.ResetAsync(cancellationToken);
    }

    public override ValueTask ResetAsync(CancellationToken cancellationToken)
    {
        return this.team.ResetAsync(cancellationToken);
    }
}
