// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionService.cs

using System;
using System.Threading.Tasks;
using AutoGen.Core;
using AutoGen.Service.OpenAI.DTO;
using Microsoft.AspNetCore.Mvc;

namespace AutoGen.Server;

public class OpenAIChatCompletionService
{
    private readonly IAgent agent;

    public OpenAIChatCompletionService(IAgent agent)
    {
        this.agent = agent;
    }

    [HttpPost("v1/chat/completions")]
    public async Task<OpenAIChatCompletion> GetChatCompletionAsync(OpenAIChatCompletionOption request)
    {
        throw new NotImplementedException();
    }
}
