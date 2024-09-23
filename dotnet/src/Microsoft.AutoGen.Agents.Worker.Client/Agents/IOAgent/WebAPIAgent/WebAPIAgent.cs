using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Worker.Client;

public class WebAPIAgent : IOAgent<AgentState>,
        IUseWebAPI,
        IHandle<Input>,
        IHandle<Output>
{
    private readonly string _url = "/agents/webio";

    public WebAPIAgent(
    IAgentContext context,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    string url,
    ILogger<WebAPIAgent> logger) : base(
        context,
        typeRegistry)
    {
        _url = url;
        var builder = WebApplication.CreateBuilder();
        var app = builder.Build();

        app.MapPost(_url, async (HttpContext httpContext) =>
        {
            var input = await httpContext.Request.ReadFromJsonAsync<Input>();
            if (input != null)
            {
                await Handle(input);
                await httpContext.Response.WriteAsync("Input processed");
            }
            else
            {
                httpContext.Response.StatusCode = 400;
                await httpContext.Response.WriteAsync("Invalid input");
            }
        });

        app.MapGet(_url, async (HttpContext httpContext) =>
        {
            var output = new Output(); // Replace with actual output retrieval logic
            await Handle(output);
            await httpContext.Response.WriteAsJsonAsync(output);
        });

        app.Run();
    }

    public override async Task Handle(Input item)
    {
        // Process the input (this is a placeholder, replace with actual processing logic)
        await ProcessInput(item.Message);

        var evt = new InputProcessed
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public override async Task Handle(Output item)
    {
        // Assuming item has a property `Content` that we want to return in the response
        var evt = new OutputWritten
        {
            Route = _route
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public override Task<string> ProcessInput(string message)
    {
        // Implement your input processing logic here
        return Task.FromResult(message);
    }

    public override Task ProcessOutput(string message)
    {
        // Implement your output processing logic here
        return Task.CompletedTask;
    }
}

public interface IUseWebAPI
{
}