using System.Text;
using Azure;
using Azure.Core;
using Azure.Data.Tables;
using Azure.Identity;
using Azure.ResourceManager;
using Azure.ResourceManager.ContainerInstance;
using Azure.ResourceManager.ContainerInstance.Models;
using Azure.ResourceManager.Resources;
using Azure.Storage.Files.Shares;
using Microsoft.AspNetCore.Http;
using Microsoft.Azure.Functions.Worker;
using Microsoft.DurableTask.Client;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Octokit;
using Octokit.Helpers;

namespace SK.DevTeam
{
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
    public class PullRequestActivities
    {
        private readonly AzureOptions _azSettings;
        private readonly GithubService _ghService;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly ILogger<PullRequestActivities> logger;

        public PullRequestActivities(IOptions<AzureOptions> azOptions, GithubService ghService, IHttpClientFactory httpClientFactory, ILogger<PullRequestActivities> logger)
        {
            _azSettings = azOptions.Value;
            _ghService = ghService;
            _httpClientFactory = httpClientFactory;
            this.logger = logger;
        }

        [Function(nameof(SaveOutput))]
        public async Task<bool> SaveOutput([ActivityTrigger] SaveOutputRequest request, FunctionContext executionContext)
        {
            var connectionString = $"DefaultEndpointsProtocol=https;AccountName={_azSettings.FilesAccountName};AccountKey={_azSettings.FilesAccountKey};EndpointSuffix=core.windows.net";
            var parentDirName = $"{request.Directory}/{request.IssueOrchestrationId}";
            var fileName = $"{request.FileName}.{request.Extension}";

            var share = new ShareClient(connectionString, _azSettings.FilesShareName);
            await share.CreateIfNotExistsAsync();
            await share.GetDirectoryClient($"{request.Directory}").CreateIfNotExistsAsync();

            var parentDir = share.GetDirectoryClient(parentDirName);
            await parentDir.CreateIfNotExistsAsync();

            var directory = parentDir.GetSubdirectoryClient(request.SubOrchestrationId);
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

            return true;
        }

        [Function(nameof(CreateBranch))]
        public async Task<bool> CreateBranch([ActivityTrigger] GHNewBranch request, FunctionContext executionContext)
        {
            var ghClient = await _ghService.GetGitHubClient();
            var repo = await ghClient.Repository.Get(request.Org, request.Repo);
            await ghClient.Git.Reference.CreateBranch(request.Org, request.Repo, request.Branch, repo.DefaultBranch);
            return true;
        }

        [Function(nameof(CreatePR))]
        public async Task<bool> CreatePR([ActivityTrigger] GHNewBranch request, FunctionContext executionContext)
        {
            var ghClient = await _ghService.GetGitHubClient();
            var repo = await ghClient.Repository.Get(request.Org, request.Repo);
            await ghClient.PullRequest.Create(request.Org, request.Repo, new NewPullRequest($"New app #{request.Number}", request.Branch, repo.DefaultBranch));
            return true;
        }

        [Function(nameof(RunInSandbox))]

        public async Task<bool> RunInSandbox(
            [ActivityTrigger] RunInSandboxRequest request,
            [TableInput("ContainersMetadata", Connection = "AzureWebJobsStorage")] TableClient tableClient,
            FunctionContext executionContext)
        {
            var client = new ArmClient(new DefaultAzureCredential());

            var containerGroupName = $"sk-sandbox-{request.PrRequest.SubOrchestrationId}";
            var containerName = $"sk-sandbox-{request.PrRequest.SubOrchestrationId}";
            var image = Environment.GetEnvironmentVariable("SANDBOX_IMAGE", EnvironmentVariableTarget.Process);

            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = client.GetResourceGroupResource(resourceGroupResourceId);

            var scriptPath = $"/azfiles/output/{request.PrRequest.IssueOrchestrationId}/{request.PrRequest.SubOrchestrationId}/run.sh";

            var collection = resourceGroupResource.GetContainerGroups();

            var data = new ContainerGroupData(new AzureLocation(_azSettings.Location), new ContainerInstanceContainer[]
            {
                    new ContainerInstanceContainer(containerName,image,new ContainerResourceRequirements(new ContainerResourceRequestsContent(1.5,1)))
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
            await collection.CreateOrUpdateAsync(WaitUntil.Completed, containerGroupName, data);

            var metadata = new ContainerInstanceMetadata
            {
                PartitionKey = containerGroupName,
                RowKey = containerGroupName,
                SubOrchestrationId = request.SanboxOrchestrationId,
                Processed = false
            };
            await tableClient.UpsertEntityAsync(metadata);
            return true;
        }

        [Function(nameof(CommitToGithub))]
        public async Task<bool> CommitToGithub([ActivityTrigger] GHCommitRequest request, FunctionContext executionContext)
        {
            var connectionString = $"DefaultEndpointsProtocol=https;AccountName={_azSettings.FilesAccountName};AccountKey={_azSettings.FilesAccountKey};EndpointSuffix=core.windows.net";
            var ghClient = await _ghService.GetGitHubClient();

            var dirName = $"{request.Directory}/{request.IssueOrchestrationId}/{request.SubOrchestrationId}";
            var share = new ShareClient(connectionString, _azSettings.FilesShareName);
            var directory = share.GetDirectoryClient(dirName);

            var remaining = new Queue<ShareDirectoryClient>();
            remaining.Enqueue(directory);
            while (remaining.Count > 0)
            {
                var dir = remaining.Dequeue();
                await foreach (var item in dir.GetFilesAndDirectoriesAsync())
                {
                    if (!item.IsDirectory && item.Name != "run.sh") // we don't want the generated script in the PR
                    {
                        try
                        {
                            var file = dir.GetFileClient(item.Name);
                            var filePath = file.Path.Replace($"{_azSettings.FilesShareName}/", "")
                                                    .Replace($"{dirName}/", "");
                            var fileStream = await file.OpenReadAsync();
                            using (var reader = new StreamReader(fileStream, Encoding.UTF8))
                            {
                                var value = reader.ReadToEnd();

                                await ghClient.Repository.Content.CreateFile(
                                        request.Org, request.Repo, filePath,
                                        new CreateFileRequest($"Commit message", value, request.Branch)); // TODO: add more meaningfull commit message
                            }
                        }
                        catch (Exception ex)
                        {
                            logger.LogError(ex, $"Error while uploading file {item.Name}");
                        }
                    }
                    else if (item.IsDirectory)
                    {
                        remaining.Enqueue(dir.GetSubdirectoryClient(item.Name));
                    }
                }
            }

            return true;
        }

        [Function(nameof(Terminated))]
        public async Task<ContainerInstanceMetadata> Terminated(
            [HttpTrigger(AuthorizationLevel.Anonymous, "post", Route = "container/{name}/terminate")] HttpRequest req,
            [TableInput("ContainersMetadata", Connection = "AzureWebJobsStorage")] TableClient tableClient,
            [DurableClient] DurableTaskClient client)
        {
            var containerGroupName = req.RouteValues["name"].ToString();
            var metadataResponse = await tableClient.GetEntityAsync<ContainerInstanceMetadata>(containerGroupName, containerGroupName);
            var metadata = metadataResponse.Value;
            if (!metadata.Processed)
            {
                await client.RaiseEventAsync(metadata.SubOrchestrationId, SubIssueOrchestration.ContainerTerminated, true);
                metadata.Processed = true;
                await tableClient.UpdateEntityAsync(metadata, metadata.ETag, TableUpdateMode.Replace);
            }

            return metadata;
        }

        [Function(nameof(CleanContainers))]
        public async Task CleanContainers(
            [TimerTrigger("*/30 * * * * *")] TimerInfo myTimer,
            FunctionContext executionContext)
        {
            var httpClient = _httpClientFactory.CreateClient("FunctionsClient");
            var client = new ArmClient(new DefaultAzureCredential());
            var resourceGroupResourceId = ResourceGroupResource.CreateResourceIdentifier(_azSettings.SubscriptionId, _azSettings.ContainerInstancesResourceGroup);
            var resourceGroupResource = client.GetResourceGroupResource(resourceGroupResourceId);

            var collection = resourceGroupResource.GetContainerGroups();

            foreach (var cg in collection.GetAll())
            {
                var c = await cg.GetAsync();
                if (c.Value.Data.ProvisioningState == "Succeeded"
                && c.Value.Data.Containers.First().InstanceView.CurrentState.State == "Terminated")
                {
                    await cg.DeleteAsync(WaitUntil.Started);
                    await httpClient.PostAsync($"container/{cg.Data.Name}/terminate", default);
                }
            }
        }
    }
}