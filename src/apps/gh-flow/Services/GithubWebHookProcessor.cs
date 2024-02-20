using Microsoft.AI.DevTeam;
using Microsoft.AI.DevTeam.Skills;
using Octokit.Webhooks;
using Octokit.Webhooks.Events;
using Octokit.Webhooks.Events.IssueComment;
using Octokit.Webhooks.Events.Issues;
using Octokit.Webhooks.Models;
using Orleans.Runtime;

public sealed class GithubWebHookProcessor : WebhookEventProcessor
{
    private readonly ILogger<GithubWebHookProcessor> _logger;
    private readonly IClusterClient _client;
    private readonly IManageGithub _ghService;
    private readonly IManageAzure _azService;

    public GithubWebHookProcessor(ILogger<GithubWebHookProcessor> logger,
    IClusterClient client, IManageGithub ghService, IManageAzure azService)
    {
        _logger = logger;
        _client = client;
        _ghService = ghService;
        _azService = azService;
    }
    protected override async Task ProcessIssuesWebhookAsync(WebhookHeaders headers, IssuesEvent issuesEvent, IssuesAction action)
    {
        try
        {
            _logger.LogInformation("Processing issue event");
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
                _logger.LogInformation("Processing HandleNewAsk");
                await HandleNewAsk(issueNumber, skillName, functionName, suffix, input, org, repo);
            }
            else if (issuesEvent.Action == IssuesAction.Closed && issuesEvent.Issue.User.Type.Value == UserType.Bot)
            {
                _logger.LogInformation("Processing HandleClosingIssue");
                await HandleClosingIssue(issueNumber, skillName, functionName, suffix, org, repo);
            }
        }
        catch (System.Exception)
        {
             _logger.LogError("Processing issue event");
        }
    }

    protected override async Task ProcessIssueCommentWebhookAsync(
       WebhookHeaders headers,
       IssueCommentEvent issueCommentEvent,
       IssueCommentAction action)
    {
        try
        {
            _logger.LogInformation("Processing issue comment event");
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
        catch (System.Exception ex)
        {
            _logger.LogError("Processing issue comment event");
        }
       
    }

    private async Task HandleClosingIssue(long issueNumber, string skillName, string functionName, string suffix, string org, string repo)
    {
        var streamProvider = _client.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(suffix, issueNumber.ToString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.OnNextAsync(new Event
        {
            Type = EventType.ChainClosed,
            Org = org,
            Repo = repo,
            IssueNumber = issueNumber
        });
    }

    private async Task HandleNewAsk(long issueNumber, string skillName, string functionName, string suffix, string input, string org, string repo)
    {
        try
        {
            _logger.LogInformation("Handling new ask");
            var streamProvider = _client.GetStreamProvider("StreamProvider");
            var streamId = StreamId.Create("DevPersonas", suffix+issueNumber.ToString());
            var stream = streamProvider.GetStream<Event>(streamId);

            var eventType = (skillName, functionName) switch
            {
                ("Do", "It") => EventType.NewAsk,
                (nameof(PM), nameof(PM.Readme)) => EventType.NewAskReadme,
                (nameof(DevLead), nameof(DevLead.Plan)) => EventType.NewAskPlan,
                (nameof(Developer), nameof(Developer.Implement)) => EventType.NewAskImplement,
                _ => EventType.NewAsk
            };
            await stream.OnNextAsync(new Event
            {
                Type = eventType,
                Message = input,
                Org = org,
                Repo = repo,
                IssueNumber = issueNumber
            });

            // else if (skillName == "Repo" && functionName == "Ingest")
            // {
            //     var ingestor = _grains.GetGrain<IIngestRepo>(suffix);
            //     await ingestor.IngestionFlow(org, repo, "main");
            // }
        }
        catch (System.Exception)
        {
             _logger.LogError("Handling new ask");
        }
        
    }
}

