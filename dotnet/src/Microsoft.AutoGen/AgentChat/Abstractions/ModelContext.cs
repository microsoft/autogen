// Copyright (c) Microsoft Corporation. All rights reserved.
// ModelContext.cs

using System.Text.Json;
using Microsoft.AutoGen.AgentChat.State;
using Microsoft.AutoGen.Contracts;

using LLMMessage = Microsoft.Extensions.AI.ChatMessage;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public interface IModelContext : ISaveState
{
    public void Add(LLMMessage message);
    public void Clear();

    public IEnumerable<LLMMessage> Messages { get; }
}

public sealed class ModelContextState : BaseState
{
    public List<LLMMessage> Messages { get; set; } = new();
}

public abstract class ModelContextBase : IModelContext
{
    protected readonly List<LLMMessage> messages;

    public abstract IEnumerable<LLMMessage> Messages { get; }

    public ModelContextBase(params IEnumerable<LLMMessage> messages)
    {
        this.messages = [.. messages];
    }

    public void Add(LLMMessage message)
    {
        this.messages.Add(message);
    }

    public void Clear()
    {
        this.messages.Clear();
    }

    public ValueTask<JsonElement> SaveStateAsync()
    {
        SerializedState state = SerializedState.Create(new ModelContextState { Messages = this.messages });
        return ValueTask.FromResult(state.AsJson());
    }

    public ValueTask LoadStateAsync(JsonElement state)
    {
        SerializedState serializedState = new(state);
        ModelContextState modelContextState = serializedState.As<ModelContextState>();

        this.messages.Clear();
        this.messages.AddRange(modelContextState.Messages);

        return ValueTask.CompletedTask;
    }
}

public sealed class UnboundedModelContext : ModelContextBase
{
    public UnboundedModelContext(params IEnumerable<LLMMessage> messages) : base(messages)
    {
    }

    public override IEnumerable<LLMMessage> Messages => this.messages;
}

// TODO: Promote ModelContext to AutoGen.Core
