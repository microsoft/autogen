using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents
{
    public interface IAgentBase
    {
        // Properties
        string AgentId { get; }
        ILogger Logger { get; }
        IAgentContext Context { get; }

        // Methods
        Task CallHandler(CloudEvent item);
        Task<RpcResponse> HandleRequest(RpcRequest request);
        Task Start();
        Task ReceiveMessage(Message message);
        Task Store(AgentState state);
        Task<T> Read<T>(AgentId agentId);
        Task PublishEvent(CloudEvent item);
    }
}
