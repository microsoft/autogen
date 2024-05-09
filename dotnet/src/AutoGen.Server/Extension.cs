// Copyright (c) Microsoft Corporation. All rights reserved.
// Extension.cs

using AutoGen.Core;
using Microsoft.AspNetCore.Builder;

namespace AutoGen.Service;

public static class Extension
{
    /// <summary>
    /// Serve the agent as an OpenAI chat completion endpoint using <see cref="OpenAIChatCompletionMiddleware"/>.
    /// The endpoint will be available at /v1/chat/completions
    /// </summary>
    /// <param name="app">application builder</param>
    /// <param name="agent"><see cref="IAgent"/></param>
    public static IApplicationBuilder UseAgentAsOpenAIChatCompletionEndpoint(this IApplicationBuilder app, IAgent agent)
    {
        var middleware = new OpenAIChatCompletionMiddleware(agent);
        return app.Use(middleware.InvokeAsync);
    }
}
