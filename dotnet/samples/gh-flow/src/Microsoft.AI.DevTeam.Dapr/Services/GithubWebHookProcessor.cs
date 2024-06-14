using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.DevTeam.Dapr.Events;
using Octokit.Webhooks;
using Octokit.Webhooks.Events;
using Octokit.Webhooks.Events.IssueComment;
using Octokit.Webhooks.Events.Issues;
using Octokit.Webhooks.Models;

namespace Microsoft.AI.DevTeam.Dapr;
public sealed class GithubWebHookProcessor : WebhookEventProcessor
{
    private readonly DaprClient _daprClient;
    private readonly ILogger<GithubWebHookProcessor> _logger;

    public GithubWebHookProcessor(DaprClient daprClient, ILogger<GithubWebHookProcessor> logger)
    {
        _daprClient = daprClient;
        _logger = logger;
    }
    protected override async Task ProcessIssuesWebhookAsync(WebhookHeaders headers, IssuesEvent issuesEvent, IssuesAction action)
    {
        try
        {
            _logger.LogInformation("Processing issue event");
            var org = issuesEvent.Repository.Owner.Login;
            var repo = issuesEvent.Repository.Name;
            var issueNumber = issuesEvent.Issue.Number;
            var input = issuesEvent.Issue.Body;
            // Assumes the label follows the following convention: Skill.Function example: PM.Readme
            // Also, we've introduced the Parent label, that ties the sub-issue with the parent issue
            var labels = issuesEvent.Issue.Labels
                                    .Select(l => l.Name.Split('.'))
                                    .Where(parts => parts.Length == 2)
                                    .ToDictionary(parts => parts[0], parts => parts[1]);
            var skillName = labels.Keys.Where(k => k != "Parent").FirstOrDefault();
            long? parentNumber = labels.ContainsKey("Parent") ? long.Parse(labels["Parent"]) : null;

            var suffix = $"{org}-{repo}";
            if (issuesEvent.Action == IssuesAction.Opened)
            {
                _logger.LogInformation("Processing HandleNewAsk");
                await HandleNewAsk(issueNumber, parentNumber, skillName, labels[skillName], input, org, repo);
            }
            else if (issuesEvent.Action == IssuesAction.Closed && issuesEvent.Issue.User.Type.Value == UserType.Bot)
            {
                _logger.LogInformation("Processing HandleClosingIssue");
                await HandleClosingIssue(issueNumber, parentNumber, skillName, labels[skillName], org, repo);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Processing issue event");
            throw;
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
            var org = issueCommentEvent.Repository.Owner.Login;
            var repo = issueCommentEvent.Repository.Name;
            var issueNumber = issueCommentEvent.Issue.Number;
            var input = issueCommentEvent.Comment.Body;
            // Assumes the label follows the following convention: Skill.Function example: PM.Readme
            var labels = issueCommentEvent.Issue.Labels
                                    .Select(l => l.Name.Split('.'))
                                    .Where(parts => parts.Length == 2)
                                    .ToDictionary(parts => parts[0], parts => parts[1]);
            var skillName = labels.Keys.Where(k => k != "Parent").FirstOrDefault();
            long? parentNumber = labels.ContainsKey("Parent") ? long.Parse(labels["Parent"]) : null;
            var suffix = $"{org}-{repo}";
            // we only respond to non-bot comments
            if (issueCommentEvent.Sender.Type.Value != UserType.Bot)
            {
                await HandleNewAsk(issueNumber, parentNumber, skillName, labels[skillName], input, org, repo);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Processing issue comment event");
            throw;
        }

    }

    private async Task HandleClosingIssue(long issueNumber, long? parentNumber, string skillName, string functionName, string org, string repo)
    {
        var subject = $"{org}-{repo}-{issueNumber}";
        var eventType = (skillName, functionName) switch
        {
            ("PM", "Readme") => nameof(GithubFlowEventType.ReadmeChainClosed),
            ("DevLead", "Plan") => nameof(GithubFlowEventType.DevPlanChainClosed),
            ("Developer", "Implement") => nameof(GithubFlowEventType.CodeChainClosed),
            _ => nameof(GithubFlowEventType.NewAsk)
        };
        var data = new Dictionary<string, string>
        {
            { "org", org },
            { "repo", repo },
            { "issueNumber", issueNumber.ToString() },
            { "parentNumber", parentNumber?.ToString()}
        };

        var evt = new Event
        {
            Type = eventType,
            Subject = subject,
            Data = data
        };
        await PublishEvent(evt);
    }

    private async Task HandleNewAsk(long issueNumber, long? parentNumber, string skillName, string functionName, string input, string org, string repo)
    {
        try
        {
            _logger.LogInformation("Handling new ask");
            var subject = $"{org}-{repo}-{issueNumber}";
            var eventType = (skillName, functionName) switch
            {
                ("Do", "It") => nameof(GithubFlowEventType.NewAsk),
                ("PM", "Readme") => nameof(GithubFlowEventType.ReadmeRequested),
                ("DevLead", "Plan") => nameof(GithubFlowEventType.DevPlanRequested),
                ("Developer", "Implement") => nameof(GithubFlowEventType.CodeGenerationRequested),
                _ => nameof(GithubFlowEventType.NewAsk)
            };
            var data = new Dictionary<string, string>
            {
                { "org", org },
                { "repo", repo },
                { "issueNumber", issueNumber.ToString() },
                { "parentNumber", parentNumber?.ToString()},
                { "input" , input}
            };
            var evt = new Event
            {
                Type = eventType,
                Subject = subject,
                Data = data
            };
            await PublishEvent(evt);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Handling new ask");
            throw;
        }
    }

    private async Task PublishEvent(Event evt)
    {
        var metadata = new Dictionary<string, string>() {
                 { "cloudevent.Type", evt.Type },
                 { "cloudevent.Subject",  evt.Subject },
                 { "cloudevent.id", Guid.NewGuid().ToString()}
            };

        await _daprClient.PublishEventAsync(Consts.PubSub, Consts.MainTopic, evt, metadata);
    }
}



