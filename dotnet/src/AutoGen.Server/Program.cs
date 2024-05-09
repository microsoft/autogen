// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using AutoGen.Server;
using AutoGen.Service.OpenAI.DTO;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.UseOneOfForPolymorphism();
    c.UseAllOfForInheritance();

});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();


app.MapPost("/", async (OpenAIChatCompletionOption request) =>
{
    var chatCompletion = await app.Services.GetRequiredService<OpenAIChatCompletionService>().GetChatCompletionAsync(request);
    return chatCompletion;
})
.WithOpenApi();

app.Run();
