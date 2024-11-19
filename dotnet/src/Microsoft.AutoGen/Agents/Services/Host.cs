// Copyright (c) Microsoft Corporation. All rights reserved.
// Host.cs

using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Hosting;

namespace Microsoft.AutoGen.Agents;

public static class Host
{
    public static async Task<WebApplication> StartAsync(bool local = false, bool useGrpc = true)
    {
        var builder = WebApplication.CreateBuilder();
        builder.AddServiceDefaults();
        if (local)
        {
            builder.AddLocalAgentService(useGrpc: useGrpc);
        }
        else
        {
            builder.AddAgentService(useGrpc: useGrpc);
        }
        var app = builder.Build();
        app.MapAgentService(local, useGrpc);
        app.MapDefaultEndpoints();
        await app.StartAsync().ConfigureAwait(false);
        return app;
    }
}
