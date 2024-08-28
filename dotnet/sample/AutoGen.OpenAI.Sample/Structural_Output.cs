// Copyright (c) Microsoft Corporation. All rights reserved.
// Structural_Output.cs

using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using FluentAssertions;
using Json.Schema;
using Json.Schema.Generation;
using OpenAI;
using OpenAI.Chat;

namespace AutoGen.OpenAI.Sample;

internal class Structural_Output
{
    public static async Task RunAsync()
    {
        #region create_agent
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
        var model = "gpt-4o-mini";

        var schemaBuilder = new JsonSchemaBuilder().FromType<Person>();
        var schema = schemaBuilder.Build();

        var personSchemaFormat = ChatResponseFormat.CreateJsonSchemaFormat(
            name: "Person",
            jsonSchema: BinaryData.FromObjectAsJson(schema),
            description: "Person schema");

        var openAIClient = new OpenAIClient(apiKey);
        var openAIClientAgent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient(model),
            name: "assistant",
            systemMessage: "You are a helpful assistant",
            responseFormat: personSchemaFormat) // structural output by passing schema to response format
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion create_agent

        #region chat_with_agent
        var reply = await openAIClientAgent.SendAsync("My name is John, I am 25 years old, and I live in Seattle. I like to play soccer and read books.");

        var person = JsonSerializer.Deserialize<Person>(reply.GetContent());
        Console.WriteLine($"Name: {person.Name}");
        Console.WriteLine($"Age: {person.Age}");

        if (!string.IsNullOrEmpty(person.Address))
        {
            Console.WriteLine($"Address: {person.Address}");
        }

        Console.WriteLine("Done.");
        #endregion chat_with_agent

        person.Name.Should().Be("John");
        person.Age.Should().Be(25);
        person.Address.Should().BeNullOrEmpty();
        person.City.Should().Be("Seattle");
        person.Hobbies.Count.Should().Be(2);
    }
}

#region person_class
public class Person
{
    [JsonPropertyName("name")]
    [Description("Name of the person")]
    [Required]
    public string Name { get; set; }

    [JsonPropertyName("age")]
    [Description("Age of the person")]
    [Required]
    public int Age { get; set; }

    [JsonPropertyName("city")]
    [Description("City of the person")]
    public string? City { get; set; }

    [JsonPropertyName("address")]
    [Description("Address of the person")]
    public string? Address { get; set; }

    [JsonPropertyName("hobbies")]
    [Description("Hobbies of the person")]
    public List<string>? Hobbies { get; set; }
}
#endregion person_class
