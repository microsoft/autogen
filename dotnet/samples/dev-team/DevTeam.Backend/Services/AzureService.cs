// Copyright (c) Microsoft Corporation. All rights reserved.
// AzureService.cs

using System.Text;
using Azure;
using Azure.Core;
using Azure.ResourceManager;
using Azure.ResourceManager.ContainerInstance;
using Azure.ResourceManager.ContainerInstance.Models;
using Azure.ResourceManager.Resources;
using Azure.Storage.Files.Shares;
using DevTeam.Options;
using Microsoft.Extensions.Options;

namespace DevTeam.Backend.Services;

public class AzureService : IManageAzure
{
    private readonly AzureOptions _azSettings;
    private readonly ILogger<AzureService> _logger;
    private readonly ArmClient _client;

    public AzureService(IOptions<AzureOptions> azOptions, ILogger<AzureService> logger, ArmClient client)
    {
        ArgumentNullException.ThrowIfNull(azOptions);
        ArgumentNullException.ThrowIfNull(logger);
        ArgumentNullException.ThrowIfNull(client);
        _azSettings = azOptions.Value;
        _logger = logger;
        _client = client;
    }

    public async Task DeleteSandbox(string sandboxId)
    {
        try
        {
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = _client.GetResourceGroupResource(resourceGroupResourceId);

            var collection = resourceGroupResource.GetContainerGroups();
            var containerGroup = await collection.GetAsync(sandboxId);
            await containerGroup.Value.DeleteAsync(WaitUntil.Started);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting sandbox");
            throw;
        }

    }

    public async Task<bool> IsSandboxCompleted(string sandboxId)
    {
        try
        {
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = _client.GetResourceGroupResource(resourceGroupResourceId);

            var collection = resourceGroupResource.GetContainerGroups();
            var containerGroup = await collection.GetAsync(sandboxId);
            return containerGroup.Value.Data.ProvisioningState == "Succeeded"
                && containerGroup.Value.Data.Containers.First().InstanceView.CurrentState.State == "Terminated";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error checking sandbox status");
            throw;
        }
    }

    public async Task RunInSandbox(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        try
        {
            var runId = $"sk-sandbox-{org}-{repo}-{parentIssueNumber}-{issueNumber}".ToUpperInvariant();
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = _client.GetResourceGroupResource(resourceGroupResourceId);
            var scriptPath = $"/azfiles/output/{org}-{repo}/{parentIssueNumber}/{issueNumber}/run.sh";
            var collection = resourceGroupResource.GetContainerGroups();
            var data = new ContainerGroupData(new AzureLocation(_azSettings.Location), new ContainerInstanceContainer[]
            {
                    new ContainerInstanceContainer(runId, _azSettings.SandboxImage,new ContainerResourceRequirements(new ContainerResourceRequestsContent(1.5,1)))
                    {
                        Command = { "/bin/bash", $"{scriptPath}" },
                        VolumeMounts =
                        {
                            new ContainerVolumeMount("azfiles","/azfiles/")
                            {
                                IsReadOnly = false,
                            }
                        },
                    }}, ContainerInstanceOperatingSystemType.Linux)
            {
                Volumes =
                                            {
                                                new ContainerVolume("azfiles")
                                                {
                                                    AzureFile = new ContainerInstanceAzureFileVolume(_azSettings.FilesShareName,_azSettings.FilesAccountName)
                                                    {
                                                        StorageAccountKey = _azSettings.FilesAccountKey
                                                    },
                                                },
                                            },
                RestartPolicy = ContainerGroupRestartPolicy.Never,
                Sku = ContainerGroupSku.Standard,
                Priority = ContainerGroupPriority.Regular
            };
            await collection.CreateOrUpdateAsync(WaitUntil.Completed, runId, data);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error running sandbox");
            throw;
        }

    }

    public async Task Store(string org, string repo, long parentIssueNumber, long issueNumber, string filename, string extension, string dir, string output)
    {
        ArgumentNullException.ThrowIfNull(output);

        try
        {
            var connectionString = $"DefaultEndpointsProtocol=https;AccountName={_azSettings.FilesAccountName};AccountKey={_azSettings.FilesAccountKey};EndpointSuffix=core.windows.net";
            var parentDirName = $"{dir}/{org}-{repo}";

            var fileName = $"{filename}.{extension}";

            var share = new ShareClient(connectionString, _azSettings.FilesShareName);
            await share.CreateIfNotExistsAsync();
            await share.GetDirectoryClient($"{dir}").CreateIfNotExistsAsync(); ;

            var parentDir = share.GetDirectoryClient(parentDirName);
            await parentDir.CreateIfNotExistsAsync();

            var parentIssueDir = parentDir.GetSubdirectoryClient($"{parentIssueNumber}");
            await parentIssueDir.CreateIfNotExistsAsync();

            var directory = parentIssueDir.GetSubdirectoryClient($"{issueNumber}");
            await directory.CreateIfNotExistsAsync();

            var file = directory.GetFileClient(fileName);
            // hack to enable script to save files in the same directory
            var cwdHack = "#!/bin/bash\n cd $(dirname $0)";
            var contents = extension == "sh" ? output.Replace("#!/bin/bash", cwdHack, StringComparison.Ordinal) : output;
            using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(contents)))
            {
                await file.CreateAsync(stream.Length);
                await file.UploadRangeAsync(
                    new HttpRange(0, stream.Length),
                    stream);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error storing output");
            throw;
        }
    }
}

public interface IManageAzure
{
    Task Store(string org, string repo, long parentIssueNumber, long issueNumber, string filename, string extension, string dir, string output);
    Task RunInSandbox(string org, string repo, long parentIssueNumber, long issueNumber);
    Task<bool> IsSandboxCompleted(string sandboxId);
    Task DeleteSandbox(string sandboxId);
}
