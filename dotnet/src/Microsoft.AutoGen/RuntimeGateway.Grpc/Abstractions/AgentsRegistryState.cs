// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryState.cs
using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
public class AgentsRegistryState
{
    public ConcurrentDictionary<string, HashSet<string>> AgentsToEventsMap { get; set; } = new ConcurrentDictionary<string, HashSet<string>>();
    public ConcurrentDictionary<string, HashSet<string>> AgentsToTopicsMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> AgentsToTopicsPrefixMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> TopicToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> TopicPrefixToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<string>> EventsToAgentTypesMap { get; set; } = [];
    public ConcurrentDictionary<string, HashSet<Subscription>> GuidSubscriptionsMap { get; set; } = [];
    public ConcurrentDictionary<string, ConcurrentDictionary<string, IAgentRuntime>> AgentTypes { get; set; } = [];
    public string Etag { get; set; } = Guid.NewGuid().ToString();
}
