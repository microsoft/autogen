// Copyright (c) Microsoft Corporation. All rights reserved.
// ArticlesController.cs

using Marketing.Shared;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Runtime;

// For more information on enabling Web API for empty projects, visit https://go.microsoft.com/fwlink/?LinkID=397860

namespace Marketing.Backend.Controllers;

[Route("api/[controller]")]
[ApiController]
public class Articles(AgentWorker client) : ControllerBase
{
    private readonly AgentWorker _client = client;

    //// GET api/<Post>/5
    //[HttpGet("{id}")]
    //public async Task<string> Get(string id)
    //{
    //    var response = await _client.(new AgentId("writer", id), "GetArticle", []);
    //    return response.Payload.Data.ToStringUtf8();
    //}

    // PUT api/<Post>/5
    [HttpPut("{UserId}")]
    public async Task<string> Put(string userId, [FromBody] string userMessage)
    {
        ArgumentNullException.ThrowIfNull(userId);
        var evt = new UserChatInput
        {
            UserId = userId,
            UserMessage = userMessage,
        };
        await _client.PublishEventAsync(evt.ToCloudEvent(userId));

        return $"Task {userId} accepted";
    }
}
