using System;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.WriteLine("Usage: dotnet run <skillName> <functionName> <fileName>");
            return;
        }

        var skillName = args[0];
        var functionName = args[1];
        var filePath = args[2];

        if (!File.Exists(filePath))
        {
            Console.WriteLine($"File not found: {filePath}");
            return;
        }

        var variables = new[]
        {
            new { key = "input", value = File.ReadAllText(filePath) }
        };

        var requestBody = new { variables };
        var requestBodyJson = JsonSerializer.Serialize(requestBody);

        Console.WriteLine($"Calling skill '{skillName}' function '{functionName}' with file '{filePath}'");
        Console.WriteLine(requestBodyJson);

        using var httpClient = new HttpClient();
        var apiUrl = $"http://localhost:7071/api/skills/{skillName}/functions/{functionName}";
        var response = await httpClient.PostAsync(apiUrl, new StringContent(requestBodyJson));

        if (!response.IsSuccessStatusCode)
        {
            Console.WriteLine($"Error: {response.StatusCode} - {response.ReasonPhrase}");
            return;
        }

        var responseJson = await response.Content.ReadAsStringAsync();
        //if we have a successful response, we can deserialize the response body and write it to console
        var responseBody = JsonSerializer.Deserialize<object>(responseJson);
        // response body is a dictionary of key/value pairs and responseBody.response is not null, write it to console
        if (responseBody is not null && responseBody is JsonElement jsonElement && jsonElement.TryGetProperty("response", out var responseValue))
        {
            Console.WriteLine(responseValue);
        }
        else
        {
            Console.WriteLine(responseJson);
        }
        return;
    }

}