// Copyright (c) Microsoft Corporation. All rights reserved.
// SelectorGroupChat.cs

using System.Text;
using System.Text.RegularExpressions;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

using TextMessage = Microsoft.AutoGen.AgentChat.Abstractions.TextMessage;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public delegate string? SelectorFunc(List<AgentMessage> thread);

public static class MessageExtensions
{
    public static StringBuilder AppendMultiModalAsText(this StringBuilder builder, MultiModalMessage message)
    {
        foreach (var messageData in message.Content)
        {
            switch (messageData.ContentType)
            {
                case MultiModalData.Type.String:
                    TextContent textContent = (TextContent)messageData.AIContent;
                    builder.Append($" {textContent.Text}");
                    break;
                case MultiModalData.Type.Image:
                    builder.Append($" [Image]");
                    break;
            }
        }

        return builder;
    }
}

public class SelectorGroupChatManager : GroupChatManagerBase
{
    public class Options
    {
        public required IChatClient ModelClient { get; set; }

        public SelectorFunc? SelectorFunc { get; set; }

        public bool AllowRepeatedSpeaker { get; set; }

        public required PromptTemplate SelectorPrompt { get; set; }
    }

    private GroupChatOptions groupOptions;
    private Options options;

    private string? previousSpeaker;

    public SelectorGroupChatManager(GroupChatOptions groupOptions,
                                    Options selectorOptions) : base(groupOptions)
    {
        this.groupOptions = groupOptions;
        this.options = selectorOptions;
    }

    private IEnumerable<string> Roles
    {
        get
        {
            foreach (GroupParticipant participant in this.groupOptions.Participants.Values)
            {
                yield return $"{participant.TopicType}:{participant.Description}";
            }
        }
    }

    /// <summary>
    /// Counts the number of times each agent is mentioned in the provided message content.
    /// Agent names will match under any of the following conditions(all case-sensitive):
    ///
    /// - Exact name match
    /// - If the agent name has underscores it will match with spaces instead (e.g. 'Story_writer' == 'Story writer')
    /// - If the agent name has underscores it will match with '\\_' instead of '_' (e.g. 'Story_writer' == 'Story\\_writer')
    /// </summary>
    /// <param name="text">The content of the message.</param>
    /// <param name="names">A set of Agent names</param>
    /// <returns></returns>
    private IEnumerable<string> ExtractMentions(string text, IEnumerable<string> names)
    {
        foreach (string name in names)
        {
            string nameWithSpace = name.Replace("_", " ");
            string nameWithEscapedUnderscore = name.Replace("_", "\\_");

            // See https://stackoverflow.com/questions/3468102/regex-word-boundary-expressions
            string regex = $@"(?!\B\w)({Regex.Escape(name)}|{Regex.Escape(nameWithSpace)}|{Regex.Escape(nameWithEscapedUnderscore)})(?<!\w\B)";
            int count = Regex.Matches($" {text} ", regex).Count;
            if (count > 0)
            {
                yield return name;
            }
        }
    }

    private IChatClient ModelClient => this.options.ModelClient;

    public override async ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread)
    {
        if (this.options.SelectorFunc != null)
        {
            string? result = this.options.SelectorFunc(thread);
            if (result != null)
            {
                return result;
            }
        }

        List<string> historyMessages = new List<string>();
        foreach (AgentMessage message in thread)
        {
            if (message is ToolCallRequestEvent ||
                message is ToolCallExecutionEvent)
            {
                continue;
            }

            StringBuilder messageBuilder = new StringBuilder($"{message.Source}:");
            _ = message switch
            {
                TextMessage textMessage => messageBuilder.Append($" {textMessage.Content}"),
                StopMessage stopMessage => messageBuilder.Append($" {stopMessage.Content}"),
                HandoffMessage handoffMessage => messageBuilder.Append($" {handoffMessage.Context}"),
                MultiModalMessage multiModalMessage => messageBuilder.AppendMultiModalAsText(multiModalMessage),
                _ => throw new InvalidOperationException($"Unexpected message type in selector: {message.GetType()}")
            };

            historyMessages.Add(messageBuilder.ToString());
        }

        string history = string.Join("\n", historyMessages);
        string roles = string.Join("\n", this.Roles);

        IEnumerable<string> participants =
            [.. from candidaate in this.groupOptions.Participants.Values
                where this.options.AllowRepeatedSpeaker ||              // Either we allow repeated speakers, or
                      this.previousSpeaker == null ||                   // There was no previous speaker, or
                      this.previousSpeaker != candidaate.TopicType      // The candidate is not the previous speaker
                select candidaate.TopicType];

        int participantCount = this.groupOptions.Participants.Count;

        string? agentName = null;
        switch (participantCount)
        {
            case 0:
                throw new InvalidOperationException("No participants available to select from.");
            case 1:
                agentName = participants.Single();
                break;
            default:
                string prompt = this.options.SelectorPrompt.Format(
                    ("roles", roles),
                    ("participants", string.Join(", ", participants)),
                    ("history", history)).ToString();

                List<Microsoft.Extensions.AI.ChatMessage> selectMessages = [new Extensions.AI.ChatMessage(ChatRole.System, prompt)];

                ChatCompletion completion = await this.ModelClient.CompleteAsync(selectMessages);
                IEnumerable<string> mentions = this.ExtractMentions(completion.Message.Text!, participants);

                agentName = mentions.SingleOrDefault() ?? throw new InvalidOperationException($"Expected exactly one agent to be mentioned, but got {String.Join(", ", mentions)}");
                break;
        }

        this.previousSpeaker = agentName;
        return agentName;
    }
}

public class SelectorGroupChat : GroupChatBase<SelectorGroupChatManager>
{
    public const string DefaultSelectorPrompt = """
        You are in a role play game. The following roles are available:
        {roles}.

        Read the following conversation. Then select the next role from {participants} to play. Only return the role.

        {history}

        Read the above conversation. Then select the next role from {participants} to play. Only return the role.
        """;

    private SelectorGroupChatManager.Options selectorOptions;

    public SelectorGroupChat(List<IChatAgent> participants,
                             IChatClient modelClient,
                             SelectorFunc? selectorFunc = null,
                             ITerminationCondition? terminationCondition = null,
                             int? maxTurns = null,
                             bool allowRepeatedSpeaker = false,
                             string selectorPrompt = DefaultSelectorPrompt) : base(participants, terminationCondition)
    {
        PromptTemplate selectorTemplate = new PromptTemplate(selectorPrompt);
        // TODO: Validate the template parts here

        this.selectorOptions = new SelectorGroupChatManager.Options()
        {
            SelectorFunc = selectorFunc,
            ModelClient = modelClient,

            AllowRepeatedSpeaker = allowRepeatedSpeaker,
            SelectorPrompt = selectorTemplate
        };

    }

    public override SelectorGroupChatManager CreateChatManager(GroupChatOptions groupOptions)
    {
        return new SelectorGroupChatManager(groupOptions, this.selectorOptions);
    }
}
