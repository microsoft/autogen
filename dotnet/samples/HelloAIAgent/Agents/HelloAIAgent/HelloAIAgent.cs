using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;

namespace Hello;

[TopicSubscription("HelloAgents")]
public class HelloAIAgent(
    IAgentContext context,
    FromKeyedServices("EventTypes")] EventTypes typeRegistry) : HelloAgent(
        context,
        typeRegistry),
        ISayHelloAI,
        IHandle<ReceiveStory>
{
    public async Task Handle(ReceiveStory item)
    {
        var response = await SayHelloAI(item.Story).ConfigureAwait(false);
        var evt = new Output
        {
            Message = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt).ConfigureAwait(false);
        var goodbye = new ConversationClosed
        {
            UserId = this.AgentId.Key,
            UserMessage = "Goodbye"
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(goodbye).ConfigureAwait(false);
    }
    public async Task<string> SayHelloAI(string ask)
    {
        var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
        return response;
    }
    public interface ISayHelloAI
    {
        Task<string> SayHelloAI(string ask);
    }
}