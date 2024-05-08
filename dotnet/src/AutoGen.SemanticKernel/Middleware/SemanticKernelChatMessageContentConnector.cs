// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelChatMessageContentConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;

namespace AutoGen.SemanticKernel;

/// <summary>
/// This middleware converts the incoming <see cref="IMessage"/> to <see cref="ChatMessageContent"/> before passing to agent.
/// And converts the reply message from <see cref="ChatMessageContent"/> to <see cref="IMessage"/> before returning to the caller.
/// 
/// <para>requirement for agent</para>
/// <para>- Input message type: <see cref="IMessage{T}"/> where T is <see cref="ChatMessageContent"/></para>
/// <para>- Reply message type: <see cref="IMessage{T}"/> where T is <see cref="ChatMessageContent"/></para>
/// <para>- (streaming) Reply message type: <see cref="IMessage{T}"/> where T is <see cref="StreamingChatMessageContent"/></para>
/// 
/// This middleware supports the following message types:
/// <para>- <see cref="TextMessage"/></para>
/// <para>- <see cref="ImageMessage"/></para>
/// <para>- <see cref="MultiModalMessage"/></para>
/// 
/// This middleware returns the following message types:
/// <para>- <see cref="TextMessage"/></para>
/// <para>- <see cref="ImageMessage"/></para>
/// <para>- <see cref="MultiModalMessage"/></para>
/// <para>- (streaming) <see cref="TextMessageUpdate"/></para>
/// </summary>
public class SemanticKernelChatMessageContentConnector : SkSequentialChatMessageContentConnector, IStreamingMiddleware
{
    public new string? Name => nameof(SemanticKernelChatMessageContentConnector);

    public Task<IAsyncEnumerable<IStreamingMessage>> InvokeAsync(MiddlewareContext context, IStreamingAgent agent, CancellationToken cancellationToken = default)
    {
        return Task.FromResult(InvokeStreamingAsync(context, agent, cancellationToken));
    }

    private async IAsyncEnumerable<IStreamingMessage> InvokeStreamingAsync(
        MiddlewareContext context,
        IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var chatMessageContents = ProcessMessage(context.Messages, agent)
            .Select(m => new MessageEnvelope<ChatMessageContent>(m));

        await foreach (var reply in await agent.GenerateStreamingReplyAsync(chatMessageContents, context.Options, cancellationToken))
        {
            yield return PostProcessStreamingMessage(reply);
        }
    }

    private IStreamingMessage PostProcessStreamingMessage(IStreamingMessage input)
    {
        return input switch
        {
            IStreamingMessage<StreamingChatMessageContent> streamingMessage => PostProcessMessage(streamingMessage),
            IMessage msg => PostProcessMessage(msg),
            _ => input,
        };
    }

    private IStreamingMessage PostProcessMessage(IStreamingMessage<StreamingChatMessageContent> streamingMessage)
    {
        var chatMessageContent = streamingMessage.Content;
        if (chatMessageContent.ChoiceIndex > 0)
        {
            throw new InvalidOperationException("Only one choice is supported in streaming response");
        }
        return new TextMessageUpdate(Role.Assistant, chatMessageContent.Content, streamingMessage.From);
    }
}
