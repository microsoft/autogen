using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.Agents.Worker.Client;

public abstract class Agent(IAgentContext context) : AgentBase(context), IAgent
{
    Task IAgent.HandleEvent(Event item) => base.HandleEvent(item);

    async Task IAgent.PublishEvent(Event item)
    {
        await base.PublishEvent(item);
    }
}
