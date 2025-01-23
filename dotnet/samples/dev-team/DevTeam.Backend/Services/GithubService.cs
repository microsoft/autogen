// Copyright (c) Microsoft Corporation. All rights reserved.
// GithubService.cs

using System.Text;
using Azure.Storage.Files.Shares;
using DevTeam.Options;
using Microsoft.Extensions.Options;
using Octokit;
using Octokit.Helpers;

namespace DevTeam.Backend.Services;

public class GithubService : IManageGithub
{
    private readonly GitHubClient _ghClient;
    private readonly AzureOptions _azSettings;
    private readonly ILogger<GithubService> _logger;
    private readonly HttpClient _httpClient;

    public GithubService(IOptions<AzureOptions> azOptions, GitHubClient ghClient, ILogger<GithubService> logger, HttpClient httpClient)
    {
        ArgumentNullException.ThrowIfNull(azOptions);
        ArgumentNullException.ThrowIfNull(ghClient);
        ArgumentNullException.ThrowIfNull(logger);
        ArgumentNullException.ThrowIfNull(httpClient);

        _ghClient = ghClient;
        _azSettings = azOptions.Value;
        _logger = logger;
        _httpClient = httpClient;
    }

    public async Task CommitToBranch(string org, string repo, long parentNumber, long issueNumber, string rootDir, string branch)
    {
        try
        {
            var connectionString = $"DefaultEndpointsProtocol=https;AccountName={_azSettings.FilesAccountName};AccountKey={_azSettings.FilesAccountKey};EndpointSuffix=core.windows.net";

            var dirName = $"{rootDir}/{org}-{repo}/{parentNumber}/{issueNumber}";
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
                            var filePath = file.Path.Replace($"{_azSettings.FilesShareName}/", "", StringComparison.OrdinalIgnoreCase)
                                                    .Replace($"{dirName}/", "", StringComparison.OrdinalIgnoreCase);
                            var fileStream = await file.OpenReadAsync();
                            using (var reader = new StreamReader(fileStream, Encoding.UTF8))
                            {
                                var value = await reader.ReadToEndAsync();

                                try
                                {
                                    // Check if the file exists
                                    var existingFiles = await _ghClient.Repository.Content.GetAllContentsByRef(org, repo, filePath, branch);
                                    var existingFile = existingFiles[0];
                                    // If the file exists, update it
                                    var updateChangeSet = await _ghClient.Repository.Content.UpdateFile(
                                        org, repo, filePath,
                                        new UpdateFileRequest("Updated file via AI", value, existingFile.Sha, branch)); // TODO: add more meaningful commit message
                                }
                                catch (NotFoundException)
                                {
                                    // If the file doesn't exist, create it
                                    var createChangeSet = await _ghClient.Repository.Content.CreateFile(
                                        org, repo, filePath,
                                        new CreateFileRequest("Created file via AI", value, branch)); // TODO: add more meaningful commit message
                                }
                                catch (Exception ex)
                                {
                                    _logger.LogError(ex, "Error while uploading file '{FileName}'.", item.Name);
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            _logger.LogError(ex, "Error while uploading file '{FileName}'.", item.Name);
                        }
                    }
                    else if (item.IsDirectory)
                    {
                        remaining.Enqueue(dir.GetSubdirectoryClient(item.Name));
                    }
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error committing to branch");
            throw;
        }
    }

    public async Task CreateBranch(string org, string repo, string branch)
    {
        try
        {
            var ghRepo = await _ghClient.Repository.Get(org, repo);
            var contents = await _ghClient.Repository.Content.GetAllContents(org, repo);
            if (!contents.Any())
            {
                // Create a new file and commit it to the repository
                var createChangeSet = await _ghClient.Repository.Content.CreateFile(
                    org,
                    repo,
                    "README.md",
                    new CreateFileRequest("Initial commit", "# Readme")
                );
            }
            await _ghClient.Git.Reference.CreateBranch(org, repo, branch, ghRepo.DefaultBranch);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating branch");
            throw;
        }
    }

    public async Task<string> GetMainLanguage(string org, string repo)
    {
        try
        {
            var languages = await _ghClient.Repository.GetAllLanguages(org, repo);
            var mainLanguage = languages.OrderByDescending(l => l.NumberOfBytes).First();
            return mainLanguage.Name;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting main language");
            throw;
        }
    }

    public async Task<int> CreateIssue(string org, string repo, string input, string function, long parentNumber)
    {
        try
        {
            var newIssue = new NewIssue($"{function} chain for #{parentNumber}")
            {
                Body = input,
            };
            newIssue.Labels.Add(function);
            newIssue.Labels.Add($"Parent.{parentNumber}");
            var issue = await _ghClient.Issue.Create(org, repo, newIssue);
            return issue.Number;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating issue");
            throw;
        }
    }

    public async Task CreatePR(string org, string repo, long number, string branch)
    {
        try
        {
            var ghRepo = await _ghClient.Repository.Get(org, repo);
            await _ghClient.PullRequest.Create(org, repo, new NewPullRequest($"New app #{number}", branch, ghRepo.DefaultBranch));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating PR");
            throw;
        }
    }

    public async Task PostComment(string org, string repo, long issueNumber, string comment)
    {
        try
        {
            await _ghClient.Issue.Comment.Create(org, repo, (int)issueNumber, comment);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error posting comment");
            throw;
        }
    }

    public async Task<IEnumerable<FileResponse>> GetFiles(string org, string repo, string branch, Func<RepositoryContent, bool> filter)
    {
        ArgumentNullException.ThrowIfNull(filter);

        try
        {
            var items = await _ghClient.Repository.Content.GetAllContentsByRef(org, repo, branch);
            return await CollectFiles(org, repo, branch, items, filter);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting files");
            throw;
        }
    }

    private async Task<IEnumerable<FileResponse>> CollectFiles(string org, string repo, string branch, IReadOnlyList<RepositoryContent> items, Func<RepositoryContent, bool> filter)
    {
        try
        {
            var result = new List<FileResponse>();
            foreach (var item in items)
            {
                if (item.Type == ContentType.File && filter(item))
                {
                    var content = await _httpClient.GetStringAsync(new Uri(item.DownloadUrl));
                    result.Add(new FileResponse
                    {
                        Name = item.Name,
                        Content = content
                    });
                }
                else if (item.Type == ContentType.Dir)
                {
                    var subItems = await _ghClient.Repository.Content.GetAllContentsByRef(org, repo, item.Path, branch);
                    result.AddRange(await CollectFiles(org, repo, branch, subItems, filter));
                }
            }
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error collecting files");
            throw;
        }
    }
}

public class FileResponse
{
    public required string Name { get; set; }
    public required string Content { get; set; }
}

public interface IManageGithub
{
    Task<int> CreateIssue(string org, string repo, string input, string functionName, long parentNumber);
    Task CreatePR(string org, string repo, long number, string branch);
    Task CreateBranch(string org, string repo, string branch);
    Task CommitToBranch(string org, string repo, long parentNumber, long issueNumber, string rootDir, string branch);

    Task PostComment(string org, string repo, long issueNumber, string comment);
    Task<IEnumerable<FileResponse>> GetFiles(string org, string repo, string branch, Func<RepositoryContent, bool> filter);
    Task<string> GetMainLanguage(string org, string repo);
}
