// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionMiddleware.cs

using System.Text.Json;
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
            context.Request.EnableBuffering();
            var body = await context.Request.ReadFromJsonAsync<OpenAIChatCompletionOption>();
            context.Request.Body.Position = 0;
            if (body is null)
            {
                // return 400 Bad Request
                context.Response.StatusCode = 400;
                return;
            }

            if (body.Model != _agent.Name)
            {
                await next(context);
                return;
            }

            if (body.Stream is true)
            {
                // Send as server side events
                context.Response.Headers.Append("Content-Type", "text/event-stream");
                context.Response.Headers.Append("Cache-Control", "no-cache");
                context.Response.Headers.Append("Connection", "keep-alive");
                await foreach (var chatCompletion in chatCompletionService.GetStreamingChatCompletionAsync(body))
                {
                    if (chatCompletion?.Choices?[0].FinishReason is "stop")
                    {
                        // the stream is done
                        // send Data: [DONE]\n\n
                        await context.Response.WriteAsync("data: [DONE]\n\n");
                        break;
                    }
                    else
                    {
                        // remove null
                        var option = new JsonSerializerOptions
                        {
                            DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
                        };
                        var data = JsonSerializer.Serialize(chatCompletion, option);
                        await context.Response.WriteAsync($"data: {data}\n\n");
                    }
                }

                return;
            }
            else
            {
                var chatCompletion = await chatCompletionService.GetChatCompletionAsync(body);
                await context.Response.WriteAsJsonAsync(chatCompletion);
                return;
            }
        }
        else
        {
            await next(context);
        }
    }
}
