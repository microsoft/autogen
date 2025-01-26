// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryState.cs
namespace Microsoft.AutoGen.Contracts;
public class AgentsRegistryState
{
    public Dictionary<string, HashSet<string>> AgentsToEventsMap { get; set; } = [];
    public Dictionary<string, HashSet<string>> AgentsToTopicsMap { get; set; } = [];
    public Dictionary<string, HashSet<string>> TopicToAgentTypesMap { get; set; } = [];
    public Dictionary<string, HashSet<string>> EventsToAgentTypesMap { get; set; } = [];
    public Dictionary<string, HashSet<Subscription>> GuidSubscriptionsMap { get; set; } = [];
    public string ETag { get; set; } = new Guid().ToString();
}
