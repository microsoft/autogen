// Copyright (c) Microsoft Corporation. All rights reserved.
// CodeExecutorAgent.cs

using System.Text.RegularExpressions;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;

using TextMessage = Microsoft.AutoGen.AgentChat.Abstractions.TextMessage;

namespace Microsoft.AutoGen.AgentChat.Agents;

// TODO: Should this live in one of the Core packages (similar to .components in python?)
public static partial class MarkdownExtensions
{
    private static readonly Regex codeBlockPattern = new Regex(@"```(?:\s*(?<language>[\w\+\-]+))?\r?\n(?<code>[\s\S]*)```", RegexOptions.Compiled | RegexOptions.Multiline);
    public static IEnumerable<CodeBlock> ExtractCodeBlocks(this string markdownText)
    {
        return codeBlockPattern.Matches(markdownText)
                               .Select((match) =>
                                   new CodeBlock
                                   {
                                       Code = match.Groups["code"].Value.TrimEnd(),
                                       Language = match.Groups["language"].Value.Trim()
                                   });
    }
}

public class CodeExecutorAgent : ChatAgentBase
{
    private const string DefaultDescription = "A computer terminal that performs no other action than running scripts (provided to it quoted in ```<language>> code blocks).";
    public CodeExecutorAgent(string name, ICodeExecutor codeExecutor, string description = DefaultDescription) : base(name, description)
    {
        CodeExecutor = codeExecutor;
    }

    public ICodeExecutor CodeExecutor { get; }

    public override IEnumerable<Type> ProducedMessageTypes => [typeof(TextMessage)];

    public override async ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> messages, CancellationToken cancellationToken)
    {
        var codeBlocks = messages.OfType<TextMessage>()
                                                    .SelectMany((textMessage) => textMessage.Content.ExtractCodeBlocks());

        var result = "No code blocks found.";
        if (codeBlocks.Any())
        {
            var codeResult = await CodeExecutor.ExecuteCodeBlocksAsync(codeBlocks, cancellationToken);
            result = codeResult.Output;
        }

        return new Response { Message = new TextMessage { Content = result, Source = Name } };
    }

    public override ValueTask ResetAsync(CancellationToken cancellationToken)
    {
        return ValueTask.CompletedTask;
    }
}
