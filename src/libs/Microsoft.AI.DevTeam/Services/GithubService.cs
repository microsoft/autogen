using System.Text;
using Azure.Storage.Files.Shares;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Octokit;
using Octokit.Helpers;


namespace Microsoft.AI.DevTeam;

public class GithubService : IManageGithub
{
    private readonly GitHubClient _ghClient;
    private readonly AzureOptions _azSettings;
    private readonly ILogger<GithubService> _logger;
    private readonly HttpClient _httpClient;

    public GithubService(IOptions<AzureOptions> azOptions, GitHubClient ghClient, ILogger<GithubService> logger, HttpClient httpClient)
    {
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
                            var filePath = file.Path.Replace($"{_azSettings.FilesShareName}/", "")
                                                    .Replace($"{dirName}/", "");
                            var fileStream = await file.OpenReadAsync();
                            using (var reader = new StreamReader(fileStream, Encoding.UTF8))
                            {
                                var value = reader.ReadToEnd();

                                await _ghClient.Repository.Content.CreateFile(
                                        org, repo, filePath,
                                        new CreateFileRequest($"Commit message", value, branch)); // TODO: add more meaningfull commit message
                            }
                        }
                        catch (Exception ex)
                        {
                            _logger.LogError(ex, $"Error while uploading file {item.Name}");
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
                    var content = await _httpClient.GetStringAsync(item.DownloadUrl);
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
    public string Name { get; set; }
    public string Content { get; set; }
}

public interface IManageGithub
{
    Task<int> CreateIssue(string org, string repo, string input, string function, long parentNumber);
    Task CreatePR(string org, string repo, long number, string branch);
    Task CreateBranch(string org, string repo, string branch);
    Task CommitToBranch(string org, string repo, long parentNumber, long issueNumber, string rootDir, string branch);

    Task PostComment(string org, string repo, long issueNumber, string comment);
    Task<IEnumerable<FileResponse>> GetFiles(string org, string repo, string branch, Func<RepositoryContent, bool> filter);
    Task<string> GetMainLanguage(string org, string repo);
}

[GenerateSerializer]
public class NewIssueResponse
{
    [Id(0)]
    public int IssueNumber { get; set; }
    [Id(1)]
    public int CommentId { get; set; }
}
