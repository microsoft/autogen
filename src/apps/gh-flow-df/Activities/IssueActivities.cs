using Microsoft.AspNetCore.Http;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.DurableTask.Client;
using Octokit;

namespace SK.DevTeam
{
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
    public class IssuesActivities
    {
        private readonly GithubService _ghService;

        public IssuesActivities(GithubService githubService)
        {
            _ghService = githubService;
        }

        [Function(nameof(CreateIssue))]
        public async Task<NewIssueResponse> CreateIssue([ActivityTrigger] NewIssueRequest request, FunctionContext executionContext)
        {
            var ghClient = await _ghService.GetGitHubClient();
            var newIssue = new NewIssue($"{request.Function} chain for #{request.IssueRequest.Number}")
            {
                Body = request.IssueRequest.Input,

            };
            newIssue.Labels.Add($"{request.Skill}.{request.Function}");
            var issue = await ghClient.Issue.Create(request.IssueRequest.Org, request.IssueRequest.Repo, newIssue);
            var commentBody = $" - [ ] #{issue.Number} - tracks {request.Skill}.{request.Function}";
            var comment = await ghClient.Issue.Comment.Create(request.IssueRequest.Org, request.IssueRequest.Repo, (int)request.IssueRequest.Number, commentBody);

            return new NewIssueResponse
            {
                Number = issue.Number,
                CommentId = comment.Id
            };
        }

        [Function("CloseSubOrchestration")]
        public async Task Close(
            [HttpTrigger(AuthorizationLevel.Anonymous, "post", Route = "close")] HttpRequestData req,
            [DurableClient] DurableTaskClient client)
        {
            var request = await req.ReadFromJsonAsync<CloseIssueRequest>();

            var ghClient = await _ghService.GetGitHubClient();
            var comment = await ghClient.Issue.Comment.Get(request.Org, request.Repo, request.CommentId);
            var updatedComment = comment.Body.Replace("[ ]", "[x]");
            await ghClient.Issue.Comment.Update(request.Org, request.Repo, request.CommentId, updatedComment);

            await client.RaiseEventAsync(request.InstanceId, SubIssueOrchestration.IssueClosed, true);
        }



        [Function(nameof(GetLastComment))]
        public async Task<string> GetLastComment([ActivityTrigger] IssueOrchestrationRequest request, FunctionContext executionContext)
        {
            var ghClient = await _ghService.GetGitHubClient();
            var icOptions = new IssueCommentRequest
            {
                Direction = SortDirection.Descending
            };
            var apiOptions = new ApiOptions
            {
                PageCount = 1,
                PageSize = 1,
                StartPage = 1
            };

            var comments = await ghClient.Issue.Comment.GetAllForIssue(request.Org, request.Repo, (int)request.Number, icOptions, apiOptions);
            return comments.First().Body;
        }
    }
}
