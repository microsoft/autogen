#!/bin/bash

# Create skdtwebapi web service
dotnet new webapi -n skdtwebapi
cd skdtwebapi

# Add required NuGet packages
dotnet add package Microsoft.AspNetCore.OData
dotnet add package Microsoft.Azure.CognitiveServices.Language

# Add configuration parameters to appsettings.json
echo '{
  "AzureOpenAIServiceEndpoint": "",
  "AIServiceKey": "",
  "AIModel": ""
}' > appsettings.json

# Add /prompt and /skills methods to ValuesController.cs
echo 'using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.CognitiveServices.Language.TextAnalytics;
using Microsoft.Extensions.Configuration;

namespace skdtwebapi.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class ValuesController : ControllerBase
    {
        private readonly IConfiguration _config;

        public ValuesController(IConfiguration config)
        {
            _config = config;
        }

        [HttpGet("skills")]
        public async Task<ActionResult<IEnumerable<string>>> GetSkills()
        {
            var credentials = new ApiKeyServiceClientCredentials(_config["AIServiceKey"]);
            var client = new TextAnalyticsClient(credentials)
            {
                Endpoint = _config["AzureOpenAIServiceEndpoint"]
            };

            var result = await client.EntitiesRecognitionGeneralAsync("en", "I am a software developer");

            return result.Entities.Select(e => e.Name).ToList();
        }

        [HttpPut("prompt")]
        public async Task<ActionResult> Prompt([FromBody] string prompt)
        {
            var credentials = new ApiKeyServiceClientCredentials(_config["AIServiceKey"]);
            var client = new TextAnalyticsClient(credentials)
            {
                Endpoint = _config["AzureOpenAIServiceEndpoint"]
            };

            var result = await client.EntitiesRecognitionGeneralAsync("en", prompt);

            return Ok();
        }
    }
}' > Controllers/ValuesController.cs

# Create skdt command line client
cd ..
dotnet new console -n skdt
cd skdt

# Add required NuGet packages
dotnet add package Microsoft.Extensions.Configuration
dotnet add package Microsoft.Extensions.Configuration.Json
dotnet add package Microsoft.Extensions.DependencyInjection
dotnet add package Microsoft.Extensions.Http
dotnet add package Microsoft.Net.Http.Headers

# Add configuration parameters to appsettings.json
echo '{
  "WebApiUrl": "https://localhost:5001",
  "AIServiceKey": "",
  "AIModel": ""
}' > appsettings.json

# Add code to Program.cs to PUT contents of text file to /prompt method
echo 'using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Http;

namespace skdt
{
    class Program
    {
        static async Task Main(string[] args)
        {
            var serviceProvider = new ServiceCollection()
                .AddHttpClient()
                .BuildServiceProvider();

            var clientFactory = serviceProvider.GetService<IHttpClientFactory>();
            var client = clientFactory.CreateClient();

            var configuration = new ConfigurationBuilder()
                .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
                .Build();

            var fileContents = await File.ReadAllTextAsync(args[0]);

            var response = await client.PutAsync($"{configuration["WebApiUrl"]}/prompt", new StringContent(fileContents));

            if (response.IsSuccessStatusCode)
            {
                Console.WriteLine("Prompt sent successfully.");
            }
            else
            {
                Console.WriteLine($"Error sending prompt: {response.StatusCode}");
            }
        }
    }
}' > Program.cs
