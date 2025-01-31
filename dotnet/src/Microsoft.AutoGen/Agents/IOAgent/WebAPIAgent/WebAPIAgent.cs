// Copyright (c) Microsoft Corporation. All rights reserved.
// WebAPIAgent.cs
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public abstract class WebAPIAgent : IOAgent,
        IUseWebAPI,
        IHandle<Input>,
        IHandle<Output>
{
    private readonly string _url = "/agents/webio";

    public WebAPIAgent(
    IAgentRuntime worker,
    [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry,
    ILogger<WebAPIAgent> logger,
    string url = "/agents/webio") : base(
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

    public override async Task Handle(Input item, CancellationToken cancellationToken = default)
    {
        // Process the input (this is a placeholder, replace with actual processing logic)
        await ProcessInput(item.Message);

        var evt = new InputProcessed
        {
            Route = _route
        };
        await PublishMessageAsync(evt);
    }

    public override async Task Handle(Output item, CancellationToken cancellationToken = default)
    {
        // Assuming item has a property `Content` that we want to return in the response
        var evt = new OutputWritten
        {
            Route = _route
        };
        await PublishMessageAsync(evt);
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
