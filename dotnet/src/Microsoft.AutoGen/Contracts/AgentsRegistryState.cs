// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryState.cs
using System.Collections.Concurrent;

namespace Microsoft.AutoGen.Contracts;
public class AgentsRegistryState
{
    public ConcurrentDictionary<string, HashSet<string>> AgentsToEventsMap { get; set; } = new ConcurrentDictionary<string, HashSet<string>>();
    public ConcurrentDictionary<string, HashSet<string>> AgentsToTopicsMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> TopicToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> EventsToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<Subscription>> GuidSubscriptionsMap { get; set; } = [];
    public ConcurrentDictionary<string, AgentId> AgentTypes { get; set; } = [];
    public string Etag { get; set; } = Guid.NewGuid().ToString();
}
