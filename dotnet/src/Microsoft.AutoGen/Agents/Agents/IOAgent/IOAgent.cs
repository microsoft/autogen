using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;

public abstract class IOAgent : AgentBase
{
    public string _route = "base";
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
