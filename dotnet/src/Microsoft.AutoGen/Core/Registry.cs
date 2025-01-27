// Copyright (c) Microsoft Corporation. All rights reserved.
// Registry.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core;
public class Registry : IRegistry
{
    public AgentsRegistryState State { get; set; }
    private readonly IRegistryStorage Storage;
    private readonly ILogger<Registry> _logger;
    private string _registryEtag;
    private const int _retries = 5;

    public Registry(IRegistryStorage storage, ILogger<Registry> logger)
    {
        _logger = logger;
        Storage = storage;
        State = Storage.ReadStateAsync().ConfigureAwait(true).GetAwaiter().GetResult();
        _registryEtag = State.Etag;
        _logger.LogInformation("Registry initialized.");
    }

    public ValueTask<List<string>> GetSubscribedAndHandlingAgentsAsync(string topic, string eventType)
    {
        UpdateStateIfStale();
        List<string> agents = [];
        // get all agent types that are subscribed to the topic
        if (State.TopicToAgentTypesMap.TryGetValue(topic, out var subscribedAgentTypes))
        {
            /*// get all agent types that are handling the event
            if (State.EventsToAgentTypesMap.TryGetValue(eventType, out var handlingAgents))
            {
                agents.AddRange(subscribedAgentTypes.Intersect(handlingAgents).ToList());
            }*/
            agents.AddRange(subscribedAgentTypes.ToList());
        }
        if (State.TopicToAgentTypesMap.TryGetValue(eventType, out var eventHandlingAgents))
        {
            agents.AddRange(eventHandlingAgents.ToList());
        }
        if (State.TopicToAgentTypesMap.TryGetValue(topic + "." + eventType, out var combo))
        {
            agents.AddRange(combo.ToList());
        }
        // instead of an exact match, we can also check for a prefix match where key starts with the eventType
        if (State.TopicToAgentTypesMap.Keys.Any(key => key.StartsWith(eventType)))
        {
            State.TopicToAgentTypesMap.Where(
                kvp => kvp.Key.StartsWith(eventType))
                .SelectMany(kvp => kvp.Value)
                .Distinct()
                .ToList()
                .ForEach(async agentType =>
                {
                    agents.Add(agentType);
                });
        }
        agents = agents.Distinct().ToList();

        return new ValueTask<List<string>>(agents);
    }
    public async ValueTask RegisterAgentTypeAsync(RegisterAgentTypeRequest registration, IAgentRuntime runtime)
    {
        var retries = _retries;
        while (!await RegisterAgentTypeWriteAsync(registration, runtime))
        {
            if (retries == 0)
            {
                throw new IOException($"Failed to register agent type after {_retries} retries.");
            }
            _logger.LogWarning("Failed to register agent type, retrying...");
            retries--;
        }
    }

    private async ValueTask<bool> RegisterAgentTypeWriteAsync(RegisterAgentTypeRequest registration, IAgentRuntime runtime, CancellationToken cancellationToken = default)
    {
        UpdateStateIfStale();
        if (registration.Type is null)
        {
            throw new InvalidOperationException("RegisterAgentType: Agent type is required.");
        }
        var agentTypes = AgentTypes.GetAgentTypesFromAssembly()
                   ?? throw new InvalidOperationException("No agent types found in the assembly");

        if (!agentTypes.Types.TryGetValue(registration.Type, out var value))
        {
            throw new InvalidOperationException($"RegisterAgentType: Invalid agent type {registration.Type}.");
        }
        try
        {
            var agentInstance = (Agent)runtime.RuntimeServiceProvider.GetRequiredService(value);
            _logger.LogWarning("Agent type {agentType} is already registered.", registration.Type);
            State.AgentTypes.TryAdd(registration.Type, agentInstance.AgentId);
        }
        catch (InvalidOperationException)
        {
            // Agent type was not yet in the registry - it won't be available in DI
            _logger.LogInformation("Agent type {agentType} is not yet registered, activating", registration.Type);
            var agent = (Agent)ActivatorUtilities.CreateInstance(runtime.RuntimeServiceProvider, instanceType: value);
            Agent.Initialize(runtime, agent);
            State.AgentTypes.TryAdd(registration.Type, agent.AgentId);
        }
        return await WriteStateAsync(State, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask SubscribeAsync(AddSubscriptionRequest subscription)
    {
        var retries = _retries;
        while (!await SubscribeWriteAsync(subscription))
        {
            if (retries == 0)
            {
                throw new IOException($"Failed to subscribe after {_retries} retries.");
            }
            _logger.LogWarning("Failed to subscribe, retrying...");
            retries--;
        }
    }
    private async ValueTask<bool> SubscribeWriteAsync(AddSubscriptionRequest subscription, CancellationToken cancellationToken = default)
    {
        UpdateStateIfStale();
        var guid = Guid.NewGuid().ToString();
        subscription.Subscription.Id = guid;
        switch (subscription.Subscription.SubscriptionCase)
        {
            //TODO: this doesnt look right
            case Subscription.SubscriptionOneofCase.TypePrefixSubscription:
                break;
            case Subscription.SubscriptionOneofCase.TypeSubscription:
                {
                    // add the topic to the set of topics for the agent type
                    State.AgentsToTopicsMap.TryGetValue(subscription.Subscription.TypeSubscription.AgentType, out var topics);
                    if (topics is null)
                    {
                        topics = new HashSet<string>();
                        State.AgentsToTopicsMap[subscription.Subscription.TypeSubscription.AgentType] = topics;
                    }
                    topics.Add(subscription.Subscription.TypeSubscription.TopicType);

                    // add the agent type to the set of agent types for the topic
                    State.TopicToAgentTypesMap.TryGetValue(subscription.Subscription.TypeSubscription.TopicType, out var agents);
                    if (agents is null)
                    {
                        agents = new HashSet<string>();
                        State.TopicToAgentTypesMap[subscription.Subscription.TypeSubscription.TopicType] = agents;
                    }
                    agents.Add(subscription.Subscription.TypeSubscription.AgentType);

                    // add the subscription by Guid
                    State.GuidSubscriptionsMap.TryGetValue(guid, out var existingSubscriptions);
                    if (existingSubscriptions is null)
                    {
                        existingSubscriptions = new HashSet<Subscription>();
                        State.GuidSubscriptionsMap[guid] = existingSubscriptions;
                    }
                    existingSubscriptions.Add(subscription.Subscription);
                    break;
                }
            default:
                throw new InvalidOperationException("Invalid subscription type");
        }
        return await WriteStateAsync(State, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask UnsubscribeAsync(RemoveSubscriptionRequest request)
    {
        var retries = _retries;
        while (!await UnsubscribeWriteAsync(request))
        {
            if (retries == 0)
            {
                throw new IOException($"Failed to unsubscribe after {_retries} retries.");
            }
            _logger.LogWarning("Failed to unsubscribe, retrying...");
            retries--;
        }
    }
    private async ValueTask<bool> UnsubscribeWriteAsync(RemoveSubscriptionRequest request, CancellationToken cancellationToken = default)
    {
        UpdateStateIfStale();
        var guid = request.Id;
        // does the guid parse?
        if (!Guid.TryParse(guid, out var _))
        {
            throw new InvalidOperationException("Invalid subscription id");
        }
        if (State.GuidSubscriptionsMap.TryGetValue(guid, out var subscriptions))
        {
            foreach (var subscription in subscriptions)
            {
                switch (subscription.SubscriptionCase)
                {
                    case Subscription.SubscriptionOneofCase.TypeSubscription:
                        {
                            // remove the topic from the set of topics for the agent type
                            State.AgentsToTopicsMap.TryGetValue(subscription.TypeSubscription.AgentType, out var topics);
                            topics?.Remove(subscription.TypeSubscription.TopicType);

                            // remove the agent type from the set of agent types for the topic
                            State.TopicToAgentTypesMap.TryGetValue(subscription.TypeSubscription.TopicType, out var agents);
                            agents?.Remove(subscription.TypeSubscription.AgentType);

                            //remove the subscription by Guid
                            State.GuidSubscriptionsMap.TryGetValue(guid, out var existingSubscriptions);
                            existingSubscriptions?.Remove(subscription);
                            break;
                        }
                    case Subscription.SubscriptionOneofCase.TypePrefixSubscription:
                        break;
                    default:
                        throw new InvalidOperationException("Invalid subscription type");
                }
            }
            State.GuidSubscriptionsMap.Remove(guid, out _);
            return await WriteStateAsync(State, cancellationToken).ConfigureAwait(false);
        }
        return true;
    }
    public ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request)
    {
        var _ = request;
        UpdateStateIfStale();
        var subscriptions = new List<Subscription>();
        foreach (var kvp in State.GuidSubscriptionsMap)
        {
            subscriptions.AddRange(kvp.Value);
        }
        return new(subscriptions);
    }
    /// <summary>
    /// in case there is a write in between our last read and now...
    /// </summary>
    private void UpdateStateIfStale()
    {
        if (State.Etag != _registryEtag)
        {
            State = Storage.ReadStateAsync().ConfigureAwait(true).GetAwaiter().GetResult();
            _registryEtag = State.Etag;
        }
    }
    /// <summary>
    ///  Writes the state to the storage.
    /// </summary>
    /// <param name="state"></param>
    /// <returns>bool true on success, false on failure</returns>
    private async ValueTask<bool> WriteStateAsync(AgentsRegistryState state, CancellationToken cancellationToken = default)
    {
        try
        {
            await Storage.WriteStateAsync(state, cancellationToken).ConfigureAwait(false);
            _registryEtag = state.Etag;
            State = state;
            return true;
        }
        catch (Exception e)
        {
            _logger.LogError(e, "Failed to write state to storage.");
            return false;
        }
    }

    public ValueTask UnregisterAgentTypeAsync(string type, IAgentRuntime worker)
    {
        throw new NotImplementedException();
    }
}

