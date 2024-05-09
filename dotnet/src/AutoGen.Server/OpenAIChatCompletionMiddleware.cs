// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionMiddleware.cs

using System.Threading.Tasks;
using AutoGen.Core;
using AutoGen.Server;
using AutoGen.Service.OpenAI.DTO;
using Microsoft.AspNetCore.Http;

namespace AutoGen.Service;

public class OpenAIChatCompletionMiddleware : Microsoft.AspNetCore.Http.IMiddleware
{
    private readonly IAgent _agent;
    private readonly OpenAIChatCompletionService chatCompletionService;

    public OpenAIChatCompletionMiddleware(IAgent agent)
    {
        _agent = agent;
        chatCompletionService = new OpenAIChatCompletionService(_agent);
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        // if HttpPost and path is /v1/chat/completions
        // get the request body
        // call chatCompletionService.GetChatCompletionAsync(request)
        // return the response

        // else
        // call next middleware
        if (context.Request.Method == HttpMethods.Post && context.Request.Path == "/v1/chat/completions")
        {
            var body = await context.Request.ReadFromJsonAsync<OpenAIChatCompletionOption>();

            if (body is null)
            {
                // return 400 Bad Request
                context.Response.StatusCode = 400;
                return;
            }
            var chatCompletion = await chatCompletionService.GetChatCompletionAsync(body);
            await context.Response.WriteAsJsonAsync(chatCompletion);

            return;
        }
        else
        {
            await next(context);
        }
    }
}
