// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatHandlerRouter.cs

using System.Text.Json;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

internal delegate ValueTask MessagePublishServicer(GroupChatEventBase event_, string topicType, CancellationToken cancellation = default);

internal interface IGroupChatHandler : IHandle<GroupChatStart>, IHandle<GroupChatAgentResponse>, IHandle<object>, ISaveState
{
    public void AttachMessagePublishServicer(MessagePublishServicer? servicer = null);
    public void DetachMessagePublishServicer() => this.AttachMessagePublishServicer(null);
}

internal sealed class GroupChatHandlerRouter<TManager> : HostableAgentAdapter,
                                                         IHandle<GroupChatStart>,
                                                         IHandle<GroupChatAgentResponse>,
                                                         IHandle<object>,
                                                         ISaveState

    where TManager : GroupChatManagerBase, IGroupChatHandler
{
    public const string DefaultDescription = "Group chat manager";

    private TManager ChatManager { get; }

    public GroupChatHandlerRouter(AgentInstantiationContext agentCtx, TManager chatManager, ILogger<BaseAgent>? logger = null) : base(agentCtx, DefaultDescription, logger)
    {
        this.ChatManager = chatManager;
        this.ChatManager.AttachMessagePublishServicer(PublishMessageServicer);
    }

    private ValueTask PublishMessageServicer(GroupChatEventBase event_, string topicType, CancellationToken cancellation = default)
    {
        return this.PublishMessageAsync(event_, new TopicId(topicType, this.Id.Key), cancellationToken: cancellation);
    }

    public ValueTask HandleAsync(GroupChatStart item, MessageContext messageContext)
        => this.ChatManager.HandleAsync(item, messageContext);

    public ValueTask HandleAsync(GroupChatAgentResponse item, MessageContext messageContext)
        => this.ChatManager.HandleAsync(item, messageContext);

    public ValueTask HandleAsync(object item, MessageContext messageContext)
        => this.ChatManager.HandleAsync(item, messageContext);

    ValueTask<JsonElement> ISaveState.SaveStateAsync()
        => this.ChatManager.SaveStateAsync();

    ValueTask ISaveState.LoadStateAsync(JsonElement state)
        => this.ChatManager.LoadStateAsync(state);
}
