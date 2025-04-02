// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentsRegistryState.cs
using System.Collections.Concurrent;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

/// <summary>
/// Stores agent subscription information such as topic and prefix mappings,
/// and maintains an ETag for concurrency checks.
/// </summary>
public class AgentsRegistryState
{
    /// <summary>
    /// Maps each agent ID to the set of topics they subscribe to.
    /// </summary>
    public ConcurrentDictionary<string, HashSet<string>> AgentsToTopicsMap { get; set; } = [];

    /// <summary>
    /// Maps each agent ID to the set of topic prefixes they subscribe to.
    /// </summary>
    public ConcurrentDictionary<string, HashSet<string>> AgentsToTopicsPrefixMap { get; set; } = [];

    /// <summary>
    /// Maps each topic name to the set of agent types subscribed to it.
    /// </summary>
    public ConcurrentDictionary<string, HashSet<string>> TopicToAgentTypesMap { get; set; } = [];

    /// <summary>
    /// Maps each topic prefix to the set of agent types subscribed to it.
    /// </summary>
    public ConcurrentDictionary<string, HashSet<string>> TopicPrefixToAgentTypesMap { get; set; } = [];

    /// <summary>
    /// Stores subscriptions by GUID
    /// </summary>
    public ConcurrentDictionary<string, HashSet<Subscription>> GuidSubscriptionsMap { get; set; } = [];

    /// <summary>
    /// The concurrency ETag for identifying the registry's version or state.
    /// </summary>
    public string Etag { get; set; } = Guid.NewGuid().ToString();
}
