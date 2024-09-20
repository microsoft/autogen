using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Worker.Client;

public abstract class IOAgent<T> : AgentBase where T : class, new()
{
    protected AgentState<T> _state;
    private readonly string _route = "console";
    
    public  IOAgent(IAgentContext context, EventTypes typeRegistry) : base(context, typeRegistry)
    {
        _state = new();
    }

    public async Task Handle(Input item)
    {
        //var processed = await ProcessInput(item.Message);
        var evt = new InputProcessed
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public abstract Task<string> ProcessInput(string message);

}