// Copyright (c) Microsoft Corporation. All rights reserved.
// SequentialRoutedAgent.cs

// TODO: Inconsistency viz Python
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

// This scaffolding is probably unneeded?
public class SequentialRoutedAgent : AgentBase
{
    public SequentialRoutedAgent(IAgentRuntime context, EventTypes eventTypes) : base(context, eventTypes)
    {
    }
}
