using System.Text.Json.Serialization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

internal sealed class KernelSettings
{
    public const string DefaultConfigFile = "config/appsettings.json";
    public const string OpenAI = "OPENAI";
    public const string AzureOpenAI = "AZUREOPENAI";
    public const string Qdrant = "QDRANT";

    [JsonPropertyName("serviceType")]
    public string ServiceType { get; set; } = string.Empty;

    [JsonPropertyName("serviceId")]
    public string ServiceId { get; set; } = string.Empty;

    [JsonPropertyName("deploymentOrModelId")]
    public string DeploymentOrModelId { get; set; } = string.Empty;
    [JsonPropertyName("embeddingDeploymentOrModelId")]
    public string EmbeddingDeploymentOrModelId { get; set; } = string.Empty;

    [JsonPropertyName("endpoint")]
    public string Endpoint { get; set; } = string.Empty;

    [JsonPropertyName("apiKey")]
    public string ApiKey { get; set; } = string.Empty;

    [JsonPropertyName("orgId")]
    public string OrgId { get; set; } = string.Empty;

    [JsonPropertyName("qdrantEndpoint")]
    public string QdrantEndpoint { get; set; } = string.Empty;

    [JsonPropertyName("logLevel")]
    public LogLevel? LogLevel { get; set; }

    /// <summary>
    /// Load the kernel settings from settings.json if the file exists and if not attempt to use user secrets.
    /// </summary>
    internal static KernelSettings LoadSettings()
    {
        try
        {
            if (File.Exists(DefaultConfigFile))
            {
                return FromFile(DefaultConfigFile);
            }

            Console.WriteLine($"Semantic kernel settings '{DefaultConfigFile}' not found, attempting to load configuration from user secrets.");

            return FromUserSecrets();
        }
        catch (InvalidDataException ide)
        {
            Console.Error.WriteLine(
                "Unable to load semantic kernel settings, please provide configuration settings using instructions in the README.\n" +
                "Please refer to: https://github.com/microsoft/semantic-kernel-starters/blob/main/sk-csharp-hello-world/README.md#configuring-the-starter"
            );
            throw new InvalidOperationException(ide.Message);
        }
    }

    /// <summary>
    /// Load the kernel settings from the specified configuration file if it exists.
    /// </summary>
    internal static KernelSettings FromFile(string configFile = DefaultConfigFile)
    {
        if (!File.Exists(configFile))
        {
            throw new FileNotFoundException($"Configuration not found: {configFile}");
        }

        var configuration = new ConfigurationBuilder()
            .SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile(configFile, optional: true, reloadOnChange: true)
            .AddEnvironmentVariables()
            .Build();

        return configuration.Get<KernelSettings>()
               ?? throw new InvalidDataException($"Invalid semantic kernel settings in '{configFile}', please provide configuration settings using instructions in the README.");
    }

    /// <summary>
    /// Load the kernel settings from user secrets.
    /// </summary>
    internal static KernelSettings FromUserSecrets()
    {
        var configuration = new ConfigurationBuilder()
            .AddUserSecrets<KernelSettings>()
            .AddEnvironmentVariables()
            .Build();

        return configuration.Get<KernelSettings>()
               ?? throw new InvalidDataException("Invalid semantic kernel settings in user secrets, please provide configuration settings using instructions in the README.");
    }
}
