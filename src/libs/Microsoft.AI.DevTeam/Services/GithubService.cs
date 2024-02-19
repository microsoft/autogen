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

    public GithubService(GitHubClient ghClient, IOptions<AzureOptions> azOptions, ILogger<GithubService> logger, HttpClient httpClient)
    {
        _ghClient = ghClient;
        _azSettings = azOptions.Value;
        _logger = logger;
        _httpClient = httpClient;
    }

    public async Task CommitToBranch(CommitRequest request)
    {
        try
        {
            var connectionString = $"DefaultEndpointsProtocol=https;AccountName={_azSettings.FilesAccountName};AccountKey={_azSettings.FilesAccountKey};EndpointSuffix=core.windows.net";

            var dirName = $"{request.Dir}/{request.Org}-{request.Repo}/{request.ParentNumber}/{request.Number}";
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
                                        request.Org, request.Repo, filePath,
                                        new CreateFileRequest($"Commit message", value, request.Branch)); // TODO: add more meaningfull commit message
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
        }
    }

    public async Task CreateBranch(CreateBranchRequest request)
    {
        try
        {
            var ghRepo = await _ghClient.Repository.Get(request.Org, request.Repo);
            await _ghClient.Git.Reference.CreateBranch(request.Org, request.Repo, request.Branch, ghRepo.DefaultBranch);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating branch");
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
            return default;
        }
    }

    public async Task<NewIssueResponse> CreateIssue(CreateIssueRequest request)
    {
        try
        {
            var newIssue = new NewIssue($"{request.Label} chain for #{request.ParentNumber}")
            {
                Body = request.Input,

            };
            newIssue.Labels.Add(request.Label);
            var issue = await _ghClient.Issue.Create(request.Org, request.Repo, newIssue);
            var commentBody = $" - [ ] #{issue.Number} - tracks {request.Label}";
            var comment = await _ghClient.Issue.Comment.Create(request.Org, request.Repo, (int)request.ParentNumber, commentBody);
            return new NewIssueResponse
            {
                IssueNumber = issue.Number,
                CommentId = comment.Id
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating issue");
            return default;
        }
    }

    public async Task CreatePR(CreatePRRequest request)
    {
        try
        {
            var ghRepo = await _ghClient.Repository.Get(request.Org, request.Repo);
            await _ghClient.PullRequest.Create(request.Org, request.Repo, new NewPullRequest($"New app #{request.Number}", request.Branch, ghRepo.DefaultBranch));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating PR");
        }

    }

    public async Task MarkTaskComplete(MarkTaskCompleteRequest request)
    {
        try
        {
            var comment = await _ghClient.Issue.Comment.Get(request.Org, request.Repo, request.CommentId);
            var updatedComment = comment.Body.Replace("[ ]", "[x]");
            await _ghClient.Issue.Comment.Update(request.Org, request.Repo, request.CommentId, updatedComment);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error marking task complete");
        }

    }

    public async Task PostComment(PostCommentRequest request)
    {
        try
        {
            await _ghClient.Issue.Comment.Create(request.Org, request.Repo, request.Number, request.Content);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error posting comment");
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
            return Enumerable.Empty<FileResponse>();
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
            return Enumerable.Empty<FileResponse>();
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
    Task<NewIssueResponse> CreateIssue(CreateIssueRequest request);
    Task MarkTaskComplete(MarkTaskCompleteRequest request);

    Task CreatePR(CreatePRRequest request);
    Task CreateBranch(CreateBranchRequest request);
    Task CommitToBranch(CommitRequest request);

    Task PostComment(PostCommentRequest request);
    Task<IEnumerable<FileResponse>> GetFiles(string org, string repo, string branch, Func<RepositoryContent, bool> filter);
    Task<string> GetMainLanguage(string org, string repo);
}

[GenerateSerializer]
public class MarkTaskCompleteRequest
{
    [Id(0)]
    public string Org { get; set; }
    [Id(1)]
    public string Repo { get; set; }
    [Id(2)]
    public int CommentId { get; set; }
}
[GenerateSerializer]
public class CreateIssueRequest
{
    [Id(0)]
    public string Input { get; set; }
    [Id(1)]
    public string Label { get; set; }
    [Id(2)]
    public long ParentNumber { get; set; }
    [Id(3)]
    public string Org { get; set; }
    [Id(4)]
    public string Repo { get; set; }
}

public class CreateBranchRequest
{
    public string Org { get; set; }
    public string Repo { get; set; }
    public string Branch { get; set; }
}

public class CreatePRRequest
{
    public string Org { get; set; }
    public string Repo { get; set; }
    public string Branch { get; set; }
    public int Number { get; set; }
}

public class PostCommentRequest
{
    public string Org { get; set; }
    public string Repo { get; set; }
    public string Content { get; set; }
    public int Number { get; set; }
}

[GenerateSerializer]
public class NewIssueResponse
{
    [Id(0)]
    public int IssueNumber { get; set; }
    [Id(1)]
    public int CommentId { get; set; }
}

[GenerateSerializer]
public class CommitRequest
{
    [Id(0)]
    public string Dir { get; set; }
    [Id(1)]
    public string Org { get; set; }
    [Id(2)]
    public string Repo { get; set; }
    [Id(3)]
    public int ParentNumber { get; set; }
    [Id(4)]
    public int Number { get; set; }
    [Id(5)]
    public string Branch { get; set; }
}