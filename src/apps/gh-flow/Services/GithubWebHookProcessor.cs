using MS.AI.DevTeam;
using Octokit.Webhooks;
using Octokit.Webhooks.Events;
using Octokit.Webhooks.Events.IssueComment;
using Octokit.Webhooks.Events.Issues;
using Octokit.Webhooks.Models;

public sealed class GithubWebHookProcessor : WebhookEventProcessor
{
    private readonly ILogger<GithubWebHookProcessor> _logger;
    private readonly IGrainFactory _grains;
    private readonly IManageGithub _ghService;
    private readonly IManageAzure _azService;

    public GithubWebHookProcessor(ILogger<GithubWebHookProcessor> logger, IGrainFactory grains, IManageGithub ghService, IManageAzure azService)
    {
        _logger = logger;
        _grains = grains;
        _ghService = ghService;
        _azService = azService;
    }
    protected override async Task ProcessIssuesWebhookAsync(WebhookHeaders headers, IssuesEvent issuesEvent, IssuesAction action)
    {
        var org = issuesEvent.Organization.Login;
        var repo = issuesEvent.Repository.Name;
        var issueNumber = issuesEvent.Issue.Number;
        var input = issuesEvent.Issue.Body;
        // Assumes the label follows the following convention: Skill.Function example: PM.Readme
        var labels = issuesEvent.Issue.Labels.First().Name.Split(".");
        var skillName = labels[0];
        var functionName = labels[1];
        var suffix = $"{org}-{repo}";
        if (issuesEvent.Action == IssuesAction.Opened)
        {
            await HandleNewAsk(issueNumber, skillName, functionName, suffix, input, org, repo);
        }
        else if (issuesEvent.Action == IssuesAction.Closed && issuesEvent.Issue.User.Type.Value == UserType.Bot)
        {
            await HandleClosingIssue(issueNumber, skillName, functionName, suffix, org, repo);
        }
    }

    protected override async Task ProcessIssueCommentWebhookAsync(
       WebhookHeaders headers,
       IssueCommentEvent issueCommentEvent,
       IssueCommentAction action)
    {
        var org = issueCommentEvent.Organization.Login;
        var repo = issueCommentEvent.Repository.Name;
        var issueNumber = issueCommentEvent.Issue.Number;
        var input = issueCommentEvent.Issue.Body;
        // Assumes the label follows the following convention: Skill.Function example: PM.Readme
        var labels = issueCommentEvent.Issue.Labels.First().Name.Split(".");
        var skillName = labels[0];
        var functionName = labels[1];
        var suffix = $"{org}-{repo}";
        // we only resond to non-bot comments
        if (issueCommentEvent.Sender.Type.Value != UserType.Bot)
        {
            await HandleNewAsk(issueNumber, skillName, functionName, suffix, input, org, repo);
        }
    }

    private async Task HandleClosingIssue(long issueNumber, string skillName, string functionName, string suffix, string org, string repo)
    {
        if (skillName == nameof(PM) && functionName == nameof(PM.Readme))
        {
            await HandleClosingReadme(issueNumber, suffix, org, repo);
        }
        else if (skillName == nameof(DevLead) && functionName == nameof(DevLead.Plan))
        {
            await HandleClosingDevPlan(issueNumber, suffix, org, repo);
        }
        else if (skillName == nameof(Dev) && functionName == nameof(Dev.Implement))
        {
            await HandleClosingDevImplement(issueNumber, suffix, org, repo);
        }
        else { } // something went wrong
    }

    private async Task HandleClosingDevImplement(long issueNumber, string suffix, string org, string repo)
    {
        var dev = _grains.GetGrain<IDevelopCode>(issueNumber, suffix);
        var code = await dev.GetLastMessage();
        var lookup = _grains.GetGrain<ILookupMetadata>(suffix);
        var parentIssue = await lookup.GetMetadata((int)issueNumber);
        await _azService.Store(new SaveOutputRequest
        {
            ParentIssueNumber = parentIssue.IssueNumber,
            IssueNumber = (int)issueNumber,
            Output = code,
            Extension = "sh",
            Directory = "output",
            FileName = "run",
            Org = org,
            Repo = repo
        });
        var sandboxRequest = new SandboxRequest
        {
            Org = org,
            Repo = repo,
            IssueNumber = (int)issueNumber,
            ParentIssueNumber = parentIssue.IssueNumber
        };
        await _azService.RunInSandbox(sandboxRequest);

        var commitRequest = new CommitRequest
        {
            Dir = "output",
            Org = org,
            Repo = repo,
            ParentNumber = parentIssue.IssueNumber,
            Number = (int)issueNumber,
            Branch = $"sk-{parentIssue.IssueNumber}"
        };
        var markTaskCompleteRequest = new MarkTaskCompleteRequest
        {
            Org = org,
            Repo = repo,
            CommentId = parentIssue.CommentId
        };

        var sandbox = _grains.GetGrain<IManageSandbox>(issueNumber, suffix);
        await sandbox.ScheduleCommitSandboxRun(commitRequest, markTaskCompleteRequest, sandboxRequest);
    }

    private async Task HandleClosingDevPlan(long issueNumber, string suffix, string org, string repo)
    {
        var devLead = _grains.GetGrain<ILeadDevelopment>(issueNumber, suffix);
        var lookup = _grains.GetGrain<ILookupMetadata>(suffix);
        var parentIssue = await lookup.GetMetadata((int)issueNumber);
        var conductor = _grains.GetGrain<IOrchestrateWorkflows>(parentIssue.IssueNumber, suffix);
        var plan = await devLead.GetLatestPlan();
        await conductor.ImplementationFlow(plan, org, repo, parentIssue.IssueNumber);

        await _ghService.MarkTaskComplete(new MarkTaskCompleteRequest
        {
            Org = org,
            Repo = repo,
            CommentId = parentIssue.CommentId
        });
    }

    private async Task HandleClosingReadme(long issueNumber, string suffix, string org, string repo)
    {
        var pm = _grains.GetGrain<IManageProduct>(issueNumber, suffix);
        var readme = await pm.GetLastMessage();
        var lookup = _grains.GetGrain<ILookupMetadata>(suffix);
        var parentIssue = await lookup.GetMetadata((int)issueNumber);
        await _azService.Store(new SaveOutputRequest
        {
            ParentIssueNumber = parentIssue.IssueNumber,
            IssueNumber = (int)issueNumber,
            Output = readme,
            Extension = "md",
            Directory = "output",
            FileName = "readme",
            Org = org,
            Repo = repo
        });
        await _ghService.CommitToBranch(new CommitRequest
        {
            Dir = "output",
            Org = org,
            Repo = repo,
            ParentNumber = parentIssue.IssueNumber,
            Number = (int)issueNumber,
            Branch = $"sk-{parentIssue.IssueNumber}"
        });
        await _ghService.MarkTaskComplete(new MarkTaskCompleteRequest
        {
            Org = org,
            Repo = repo,
            CommentId = parentIssue.CommentId
        });
    }

    private async Task HandleNewAsk(long issueNumber, string skillName, string functionName, string suffix, string input, string org, string repo)
    {
        if (skillName == "Do" && functionName == "It")
        {
            var conductor = _grains.GetGrain<IOrchestrateWorkflows>(issueNumber, suffix);
            await conductor.InitialFlow(input, org, repo, issueNumber);
        }
        else if (skillName == nameof(PM) && functionName == nameof(PM.Readme))
        {
            var pm = _grains.GetGrain<IManageProduct>(issueNumber, suffix);
            var readme = await pm.CreateReadme(input);
            await _ghService.PostComment(new PostCommentRequest
            {
                Org = org,
                Repo = repo,
                Number = (int)issueNumber,
                Content = readme
            });
        }
        else if (skillName == nameof(DevLead) && functionName == nameof(DevLead.Plan))
        {
            var devLead = _grains.GetGrain<ILeadDevelopment>(issueNumber, suffix);
            var plan = await devLead.CreatePlan(input);
            await _ghService.PostComment(new PostCommentRequest
            {
                Org = org,
                Repo = repo,
                Number = (int)issueNumber,
                Content = plan
            });
        }
        else if (skillName == nameof(Dev) && functionName == nameof(Dev.Implement))
        {
            var dev = _grains.GetGrain<IDevelopCode>(issueNumber, suffix);
            var code = await dev.GenerateCode(input);
            await _ghService.PostComment(new PostCommentRequest
            {
                Org = org,
                Repo = repo,
                Number = (int)issueNumber,
                Content = code
            });
        }
        else { }// something went wrong
    }
}