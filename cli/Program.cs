using System;
using System.CommandLine;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        var fileOption = new Option<FileInfo?>(
            name: "--file",
            description: "The file used for input to the skill function");

        var rootCommand = new RootCommand("CLI tool for the AI Dev team");
        rootCommand.AddGlobalOption(fileOption);

        var pmCommand = new Command("pm", "Commands for the PM team");
        var pmReadmeCommand = new Command("readme", "Produce a Readme for a given input");
        pmReadmeCommand.SetHandler(async (file) => await CallFunction(nameof(PM), PM.Readme , file.FullName), fileOption);

        var pmBootstrapCommand = new Command("bootstrap", "Bootstrap a project for a given input");
        pmBootstrapCommand.SetHandler(async (file) => await CallFunction(nameof(PM), PM.BootstrapProject, file.FullName), fileOption);

        pmCommand.AddCommand(pmReadmeCommand);
        pmCommand.AddCommand(pmBootstrapCommand);

        var devleadCommand = new Command("devlead", "Commands for the Dev Lead team");
        var devleadPlanCommand = new Command("plan", "Plan the work for a given input");
        devleadPlanCommand.SetHandler(async (file) => await CallFunction(nameof(DevLead), DevLead.Plan, file.FullName), fileOption);
        devleadCommand.AddCommand(devleadPlanCommand);

        var devCommand = new Command("dev", "Commands for the Dev team");
        var devPlanCommand = new Command("plan", "Implement the module for a given input");
        devPlanCommand.SetHandler(async (file) => await CallFunction(nameof(Developer), Developer.Implement, file.FullName), fileOption);
        devCommand.AddCommand(devPlanCommand);
       
        rootCommand.AddCommand(pmCommand);
        rootCommand.AddCommand(devleadCommand);
        rootCommand.AddCommand(devCommand);

        await rootCommand.InvokeAsync(args);
    }

    public static async Task CallFunction(string skillName, string functionName, string file)
    {
        if (!File.Exists(file))
        {
            Console.WriteLine($"File not found: {file}");
            return;
        }

        var variables = new[]
        {
            new { key = "input", value = File.ReadAllText(file) }
        };

        var requestBody = new { variables };
        var requestBodyJson = JsonSerializer.Serialize(requestBody);

        Console.WriteLine($"Calling skill '{skillName}' function '{functionName}' with file '{file}'");
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

public static class PM { public static string Readme = "Readme"; public static string BootstrapProject = "BootstrapProject"; }
public static class DevLead { public static string Plan="Plan"; }
public static class Developer { public static string Implement="Implement"; }