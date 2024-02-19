using System.Text;
using Azure;
using Azure.Core;
using Azure.Identity;
using Azure.ResourceManager;
using Azure.ResourceManager.ContainerInstance;
using Azure.ResourceManager.ContainerInstance.Models;
using Azure.ResourceManager.Resources;
using Azure.Storage.Files.Shares;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;


namespace Microsoft.AI.DevTeam;

public class AzureService : IManageAzure
{
    private readonly AzureOptions _azSettings;
    private readonly ILogger<AzureService> _logger;

    public AzureService(IOptions<AzureOptions> azOptions, ILogger<AzureService> logger)
    {
        _azSettings = azOptions.Value;
        _logger = logger;
    }

    public async Task DeleteSandbox(string sandboxId)
    {
        try
        {
            var client = new ArmClient(new DefaultAzureCredential());
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = client.GetResourceGroupResource(resourceGroupResourceId);

            var collection = resourceGroupResource.GetContainerGroups();
            var containerGroup = await collection.GetAsync(sandboxId);
            await containerGroup.Value.DeleteAsync(WaitUntil.Started);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error deleting sandbox");
        }

    }

    public async Task<bool> IsSandboxCompleted(string sandboxId)
    {
        try
        {
            var client = new ArmClient(new DefaultAzureCredential());
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = client.GetResourceGroupResource(resourceGroupResourceId);

            var collection = resourceGroupResource.GetContainerGroups();
            var containerGroup = await collection.GetAsync(sandboxId);
            return containerGroup.Value.Data.ProvisioningState == "Succeeded"
                && containerGroup.Value.Data.Containers.First().InstanceView.CurrentState.State == "Terminated";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error checking sandbox status");
            return false;
        }
    }

    public async Task RunInSandbox(SandboxRequest request)
    {
        try
        {
            var client = string.IsNullOrEmpty(_azSettings.ManagedIdentity) ?
                        new ArmClient(new AzureCliCredential())
                      : new ArmClient(new ManagedIdentityCredential(_azSettings.ManagedIdentity));

            var runId = $"sk-sandbox-{request.Org}-{request.Repo}-{request.ParentIssueNumber}-{request.IssueNumber}";
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = client.GetResourceGroupResource(resourceGroupResourceId);
            var scriptPath = $"/azfiles/output/{request.Org}-{request.Repo}/{request.ParentIssueNumber}/{request.IssueNumber}/run.sh";
            var collection = resourceGroupResource.GetContainerGroups();
            var data = new ContainerGroupData(new AzureLocation(_azSettings.Location), new ContainerInstanceContainer[]
            {
                    new ContainerInstanceContainer(runId,_azSettings.SandboxImage,new ContainerResourceRequirements(new ContainerResourceRequestsContent(1.5,1)))
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
        }
        
    }

    public async Task Store(SaveOutputRequest request)
    {
        try
        {
            var connectionString = $"DefaultEndpointsProtocol=https;AccountName={_azSettings.FilesAccountName};AccountKey={_azSettings.FilesAccountKey};EndpointSuffix=core.windows.net";
            var parentDirName = $"{request.Directory}/{request.Org}-{request.Repo}";

            var fileName = $"{request.FileName}.{request.Extension}";

            var share = new ShareClient(connectionString, _azSettings.FilesShareName);
            await share.CreateIfNotExistsAsync();
            await share.GetDirectoryClient($"{request.Directory}").CreateIfNotExistsAsync(); ;

            var parentDir = share.GetDirectoryClient(parentDirName);
            await parentDir.CreateIfNotExistsAsync();

            var parentIssueDir = parentDir.GetSubdirectoryClient($"{request.ParentIssueNumber}");
            await parentIssueDir.CreateIfNotExistsAsync();

            var directory = parentIssueDir.GetSubdirectoryClient($"{request.IssueNumber}");
            await directory.CreateIfNotExistsAsync();

            var file = directory.GetFileClient(fileName);
            // hack to enable script to save files in the same directory
            var cwdHack = "#!/bin/bash\n cd $(dirname $0)";
            var output = request.Extension == "sh" ? request.Output.Replace("#!/bin/bash", cwdHack) : request.Output;
            using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(output)))
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
        }
        
    }
}

public interface IManageAzure
{
    Task Store(SaveOutputRequest request);
    Task RunInSandbox(SandboxRequest request);
    Task<bool> IsSandboxCompleted(string sandboxId);
    Task DeleteSandbox(string sandboxId);
}

public class SaveOutputRequest
{
    public int ParentIssueNumber { get; set; }
    public int IssueNumber { get; set; }
    public string Output { get; set; }
    public string Extension { get; set; }
    public string Directory { get; set; }
    public string FileName { get; set; }
    public string Org { get; set; }
    public string Repo { get; set; }
}

[GenerateSerializer]
public class SandboxRequest
{
    [Id(0)]
    public string Org { get; set; }
    [Id(1)]
    public string Repo { get; set; }
    [Id(2)]
    public int IssueNumber { get; set; }
    [Id(3)]
    public int ParentIssueNumber { get; set; }
}