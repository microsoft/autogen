// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryState.cs
using System.Collections.Concurrent;

namespace Microsoft.AutoGen.Contracts;
public class AgentsRegistryState
{
    public ConcurrentDictionary<string, HashSet<string>> AgentsToEventsMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> AgentsToTopicsMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> TopicToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> EventsToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<Subscription>> GuidSubscriptionsMap { get; set; } = [];
    public ConcurrentDictionary<AgentId, IAgentRuntime> AgentTypes { get; set; } = [];
    public string Etag { get; set; } = new Guid().ToString();
}
