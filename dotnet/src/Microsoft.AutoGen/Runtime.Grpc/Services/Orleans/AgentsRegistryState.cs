// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryState.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc;

public class AgentsRegistryState
{
    public Dictionary<string, HashSet<string>> AgentsToEventsMap { get; set; } = [];
    public Dictionary<string, HashSet<string>> AgentsToTopicsMap { get; set; } = [];
    public Dictionary<string, HashSet<string>> TopicToAgentTypesMap { get; set; } = [];
    public Dictionary<string, HashSet<string>> EventsToAgentTypesMap { get; set; } = [];
    public Dictionary<string, HashSet<Subscription>> GuidSubscriptionsMap { get; set; } = [];
}
