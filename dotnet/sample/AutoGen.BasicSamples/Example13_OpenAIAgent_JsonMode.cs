// Copyright (c) Microsoft Corporation. All rights reserved.
// Example13_OpenAIAgent_JsonMode.cs

using System.Text.Json;
using System.Text.Json.Serialization;
using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;
using FluentAssertions;

namespace AutoGen.BasicSample;

public class Example13_OpenAIAgent_JsonMode
{
    public static async Task RunAsync()
    {
        #region create_agent
        var config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo(deployName: "gpt-35-turbo-0125"); // json mode only works with 0125 and later model.
        var apiKey = config.ApiKey;
        var endPoint = new Uri(config.Endpoint);

        var openAIClient = new OpenAIClient(endPoint, new Azure.AzureKeyCredential(apiKey));
        var openAIClientAgent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            name: "assistant",
            modelName: config.DeploymentName,
            systemMessage: "You are a helpful assistant designed to output JSON.",
            seed: 0, // explicitly set a seed to enable deterministic output
            responseFormat: ChatCompletionsResponseFormat.JsonObject) // set response format to JSON object to enable JSON mode
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion create_agent

        #region chat_with_agent
        var reply = await openAIClientAgent.SendAsync("My name is John, I am 25 years old, and I live in Seattle.");

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
    }
}

#region person_class
public class Person
{
    [JsonPropertyName("name")]
    public string Name { get; set; }

    [JsonPropertyName("age")]
    public int Age { get; set; }

    [JsonPropertyName("address")]
    public string Address { get; set; }
}
#endregion person_class
