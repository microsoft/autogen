using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Worker.Client;

public abstract class IOAgent<T> : AgentBase where T : class, new()
{
    protected AgentState<T> _state;
    public string _route = "base";
    
    public  IOAgent(IAgentContext context, EventTypes typeRegistry) : base(context, typeRegistry)
    {
        _state = new();
    }

    public virtual async Task Handle(Input item)
    {

        var evt = new InputProcessed
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public virtual async Task Handle(Output item)
    {
        var evt = new OutputWritten
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public abstract Task ProcessInput(string message);
    public abstract Task ProcessOutput(string message);

}