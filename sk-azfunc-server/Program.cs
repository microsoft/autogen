using System.Text.Json;
using Microsoft.Azure.WebJobs.Extensions.OpenApi.Core.Abstractions;
using Microsoft.Azure.WebJobs.Extensions.OpenApi.Core.Configurations;
using Microsoft.Azure.WebJobs.Extensions.OpenApi.Core.Enums;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.OpenApi.Models;
using Microsoft.SemanticKernel;

namespace KernelHttpServer;

public static class Program
{
    public static void Main()
    {
        var host = new HostBuilder()
            .ConfigureFunctionsWorkerDefaults()
            .ConfigureAppConfiguration(configuration =>
            {
                var config = configuration.SetBasePath(Directory.GetCurrentDirectory())
                    .AddJsonFile("local.settings.json", optional: true, reloadOnChange: true);

                var builtConfig = config.Build();
            })
            .ConfigureServices(services =>
            {
                services.AddSingleton<IOpenApiConfigurationOptions>(_ => s_apiConfigOptions);
                services.AddTransient((provider) => CreateKernel(provider));


                // return JSON with expected lowercase naming
                services.Configure<JsonSerializerOptions>(options =>
                {
                    options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
                });
            })
            .Build();

        host.Run();
    }

    private static IKernel CreateKernel(IServiceProvider provider)
    {
        var kernelSettings = KernelSettings.LoadSettings();

        var kernelConfig = new KernelConfig();
        kernelConfig.AddCompletionBackend(kernelSettings);

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning)
                .AddConsole()
                .AddDebug();
        });

        return new KernelBuilder().WithLogger(loggerFactory.CreateLogger<IKernel>()).WithConfiguration(kernelConfig).Build();
    }

    private static readonly OpenApiConfigurationOptions s_apiConfigOptions = new()
    {
        Info = new OpenApiInfo()
        {
            Version = "1.0.0",
            Title = "Semantic Kernel Azure Functions Starter",
            Description = "Azure Functions starter application for the [Semantic Kernel](https://github.com/microsoft/semantic-kernel).",
            Contact = new OpenApiContact()
            {
                Name = "Issues",
                Url = new Uri("https://github.com/microsoft/semantic-kernel-starters/issues"),
            },
            License = new OpenApiLicense()
            {
                Name = "MIT",
                Url = new Uri("https://github.com/microsoft/semantic-kernel-starters/blob/main/LICENSE"),
            }
        },
        Servers = DefaultOpenApiConfigurationOptions.GetHostNames(),
        OpenApiVersion = OpenApiVersionType.V2,
        ForceHttps = false,
        ForceHttp = false,
    };
}
