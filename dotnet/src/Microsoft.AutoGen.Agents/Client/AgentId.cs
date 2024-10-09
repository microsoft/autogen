using RpcAgentId = Microsoft.AutoGen.Agents.Abstractions.AgentId;

namespace Microsoft.AutoGen.Agents.Client;

public sealed record class AgentId(string Type, string Key)
{
    public static implicit operator RpcAgentId(AgentId agentId) => new()
    {
        Type = agentId.Type,
        Key = agentId.Key
    };

    public static implicit operator AgentId(RpcAgentId agentId) => new(agentId.Type, agentId.Key);
    public override string ToString() => $"{Type}/{Key}";
}
