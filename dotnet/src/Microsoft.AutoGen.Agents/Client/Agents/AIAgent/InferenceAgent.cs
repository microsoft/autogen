
namespace Microsoft.AutoGen.Agents.Client;
public abstract class InferenceAgent<T> : AgentBase where T : class, new()
{
    protected AgentState<T> _state;

    public InferenceAgent(
        IAgentContext context,
        EventTypes typeRegistry
        ) : base(context, typeRegistry)
    {
        _state = new();
    }

}