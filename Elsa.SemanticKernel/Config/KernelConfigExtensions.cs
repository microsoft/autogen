using Microsoft.SemanticKernel;

internal static class KernelConfigExtensions
{
    /// <summary>
    /// Adds a text completion service to the list. It can be either an OpenAI or Azure OpenAI backend service.
    /// </summary>
    /// <param name="kernelConfig"></param>
    /// <param name="kernelSettings"></param>
    /// <exception cref="Exception"></exception>
    internal static void AddCompletionBackend(this KernelConfig kernelConfig, KernelSettings kernelSettings)
    {
        switch (kernelSettings.ServiceType.ToUpperInvariant())
        {
            case KernelSettings.AzureOpenAI:
                kernelConfig.AddAzureChatCompletionService(kernelSettings.DeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey);
                break;

            case KernelSettings.OpenAI:
                kernelConfig.AddOpenAITextCompletionService(modelId: kernelSettings.DeploymentOrModelId, apiKey: kernelSettings.ApiKey, orgId: kernelSettings.OrgId, serviceId: kernelSettings.ServiceId);
                break;

            default:
                throw new  System.Exception($"Invalid service type value: {kernelSettings.ServiceType}");
        }
    }
}
