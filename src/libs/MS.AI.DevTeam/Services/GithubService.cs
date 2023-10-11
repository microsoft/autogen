using System.Text;
using Azure.Storage.Files.Shares;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Octokit;
using Octokit.Helpers;


namespace MS.AI.DevTeam;

public class GithubService : IManageGithub
{
    private readonly GitHubClient _ghClient;
    private readonly AzureOptions _azSettings;
    private readonly ILogger<GithubService> logger;

    public GithubService(GitHubClient ghClient, IOptions<AzureOptions> azOptions, ILogger<GithubService> logger)
    {
        _ghClient = ghClient;
        _azSettings = azOptions.Value;
        this.logger = logger;
    }

    public async Task CommitToBranch(CommitRequest request)
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
                        logger.LogError(ex, $"Error while uploading file {item.Name}");
                    }
                }
                else if (item.IsDirectory)
                {
                    remaining.Enqueue(dir.GetSubdirectoryClient(item.Name));
                }
            }
        }
    }

    public async Task CreateBranch(CreateBranchRequest request)
    {
        var ghRepo = await _ghClient.Repository.Get(request.Org, request.Repo);
        await _ghClient.Git.Reference.CreateBranch(request.Org, request.Repo, request.Branch, ghRepo.DefaultBranch);
    }

    public async Task<NewIssueResponse> CreateIssue(CreateIssueRequest request)
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

    public async Task CreatePR(CreatePRRequest request)
    {
        var ghRepo = await _ghClient.Repository.Get(request.Org, request.Repo);
        await _ghClient.PullRequest.Create(request.Org, request.Repo, new NewPullRequest($"New app #{request.Number}", request.Branch, ghRepo.DefaultBranch));
    }

    public async Task MarkTaskComplete(MarkTaskCompleteRequest request)
    {
        var comment = await _ghClient.Issue.Comment.Get(request.Org, request.Repo, request.CommentId);
        var updatedComment = comment.Body.Replace("[ ]", "[x]");
        await _ghClient.Issue.Comment.Update(request.Org, request.Repo, request.CommentId, updatedComment);
    }

    public async Task PostComment(PostCommentRequest request)
    {
        await _ghClient.Issue.Comment.Create(request.Org, request.Repo, request.Number, request.Content);
    }
}

public interface IManageGithub
{
    Task<NewIssueResponse> CreateIssue(CreateIssueRequest request);
    Task MarkTaskComplete(MarkTaskCompleteRequest request);

    Task CreatePR(CreatePRRequest request);
    Task CreateBranch(CreateBranchRequest request);
    Task CommitToBranch(CommitRequest request);

    Task PostComment(PostCommentRequest request);
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