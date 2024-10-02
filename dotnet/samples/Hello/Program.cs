using Microsoft.Extensions.Hosting;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;
using Microsoft.AutoGen.Agents.Runtime;
using Microsoft.Extensions.DependencyInjection;

var builder = Host.CreateApplicationBuilder(args);
builder.AddAgentService();
builder.UseOrleans(siloBuilder =>
{
    siloBuilder.UseLocalhostClustering(); ;
});
builder.AddAgentWorker("https://localhost:5000");
var app = builder.Build();
await app.StartAsync();
app.Services.GetRequiredService<AgentWorkerRuntime>();
var evt = new NewMessageReceived
{
    Message = "World"
}.ToCloudEvent("HelloAgents");
await app.WaitForShutdownAsync();

[TopicSubscription("HelloAgents")]
public class HelloAgent(
    IAgentContext context,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : ConsoleAgent(
        context,
        typeRegistry),
        ISayHello,
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>
{
    public async Task Handle(NewMessageReceived item)
    {
        var response = await SayHello(item.Message);
        var evt = new Output
        {
            Message = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task Handle(ConversationClosed item)
    {
        var goodbye = "Goodbye!";
        var evt = new Output
        {
            Message = goodbye
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task<string> SayHello(string ask)
    {
        var response = $"Hello {ask}";
        return response;
    }
}
public interface ISayHello
{
    public Task<string> SayHello(string ask);
}