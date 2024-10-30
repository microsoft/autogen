using Google.Protobuf;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents
{
    public interface IAgentBase
    {
        // Properties
        AgentId AgentId { get; }
        IAgentContext Context { get; }

        // Methods
        Task CallHandler(CloudEvent item);
        Task<RpcResponse> HandleRequest(RpcRequest request);
        void ReceiveMessage(Message message);
        Task Store(AgentState state);
        Task<T> Read<T>(AgentId agentId) where T : IMessage, new();
        ValueTask PublishEvent(CloudEvent item);
    }
}
