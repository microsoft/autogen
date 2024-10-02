using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;

namespace HelloAgents.Agents;

[TopicSubscription("HelloAgents")]
public class HelloAgent(
    IAgentContext context,
    Kernel kernel,
    ISemanticTextMemory memory,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    ILogger<HelloAgent> logger) : AiAgent<HelloAgentState>(
        context,
        memory,
        kernel,
        typeRegistry),
        ISayHello,
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>
{
    public async Task Handle(NewMessageReceived item)
    {
        var response = await SayHello(item.Message);
        var evt = new ResponseGenerated
        {
            Response = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task Handle(ConversationClosed item)
    {
        //TODO: Get msg from state
        var goodbye = ""; // _state.State.History.Last().Message
        var evt = new GoodBye
        {
            Message = goodbye
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task<string> SayHello(string ask)
    {
        try
        {
            var context = new KernelArguments { ["input"] = AppendChatHistory(ask) };
            return await CallFunction(HelloSkills.Greeting, context);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Error generating code");
            return "";
        }
    }
}

public interface ISayHello
{
    public Task<string> SayHello(string ask);
}
