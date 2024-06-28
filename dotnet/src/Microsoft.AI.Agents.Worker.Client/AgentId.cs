using RpcAgentId = Agents.AgentId;

namespace Microsoft.AI.Agents.Worker.Client;

public sealed record class AgentId(string Name, string Namespace)
{
    public static implicit operator RpcAgentId(AgentId agentId) => new()
    {
        Name = agentId.Name,
        Namespace = agentId.Namespace
    };

    public static implicit operator AgentId(RpcAgentId agentId) => new(agentId.Name, agentId.Namespace);
    public override string ToString() => $"{Name}/{Namespace}";
}
