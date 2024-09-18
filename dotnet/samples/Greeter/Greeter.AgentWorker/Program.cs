using Agents;
using Google.Protobuf;
using Greeter.AgentWorker;
using Microsoft.AutoGen.Agents.Worker.Client;
using AgentId = Microsoft.AutoGen.Agents.Worker.Client.AgentId;

var builder = WebApplication.CreateBuilder(args);

// Add service defaults & Aspire components.
builder.AddServiceDefaults();

var agentBuilder = builder.AddAgentWorker("https://agenthost");
agentBuilder.AddAgent<GreetingAgent>("greeter");
builder.Services.AddHostedService<MyBackgroundService>();
builder.Services.AddSingleton<AgentClient>();

var app = builder.Build();

app.MapDefaultEndpoints();

app.Run();

internal sealed class GreetingAgent(IAgentContext context, EventTypes typeRegistry, ILogger<GreetingAgent> logger) : AgentBase(context, typeRegistry)
{
    protected override Task<RpcResponse> HandleRequest(RpcRequest request)
    {
        logger.LogInformation("[{Id}] Received request: '{Request}'.", AgentId, request);
        return Task.FromResult(new RpcResponse() { Payload = new Payload {
            DataContentType = "text/plain",
            Data = ByteString.CopyFromUtf8("Hello, agents!"),
            DataType = "text"
        }});
    }
}

internal sealed class MyBackgroundService(ILogger<MyBackgroundService> logger, AgentClient client) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var generatedCodeId = Guid.NewGuid().ToString();
                var instanceId = Guid.NewGuid().ToString();
                var response = await client.SendRequestAsync(
                    new AgentId("greeter", "foo"),
                    "echo",
                    new Dictionary<string, string> { ["message"] = "Hello, agents!" }).ConfigureAwait(false);

                logger.LogInformation("Received response: {Response}", response);
            }
            catch (Exception exception)
            {
                logger.LogError(exception, "Error invoking request.");
            }

            await Task.Delay(TimeSpan.FromMinutes(2), stoppingToken).ConfigureAwait(false);
        }
    }
}
