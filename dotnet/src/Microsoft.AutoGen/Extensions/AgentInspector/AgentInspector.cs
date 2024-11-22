using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.Extensions.AgentInspector;

public class AgentInspector
{
    public class AgentInfo(ISubscriptionsGrain subscriptionsGrain)
    {
        public string AgentName { get; set; }
        public List<string> HandledEvents { get; set; } = new();
        public List<string> EmittedEvents { get; set; } = new();
    }
    public List<AgentInfo> InspectAgents()
    {
        var agents = new List<AgentInfo>();
        var _subscriptions = subscriptionsGrain.GetSubscriptions().Result;
        foreach (var agent in _subscriptions)
        {
            var agentInfo = new AgentInfo
            {
                AgentName = agent.Key
                HandledEvents = agent.Value
                EmittedEvents = GetEmittedEvents(agent.Key)
            };
            agents.Add(agentInfo);
        }
        return agents;
    }
    private List<string> GetEmittedEvents(string agentName)
    {
        // we learn what events an agent can omit by scanning all its methods and looking for calls to PublishMessage or PublishEvent and determining hat types are passed to them. 
        var agentType = Type.GetType(agentName);
        var emittedEvents = new List<string>();
        foreach (var method in agentType.GetMethods())
        {
            // does this method call PublishMessageAsync or PublishEventAsync?
            
            var body = method.GetMethodBody();

            if (body != null)
            {
                // does the content of this method include a call to PublishMessageAsync or PublishEventAsync?
                var il = body.GetILAsByteArray();
            

            }

        return emittedEvents;
    }
}