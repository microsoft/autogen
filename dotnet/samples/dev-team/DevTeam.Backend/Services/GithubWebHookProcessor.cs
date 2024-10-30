using System.Globalization;
using DevTeam.Shared;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Octokit.Webhooks;
using Octokit.Webhooks.Events;
using Octokit.Webhooks.Events.IssueComment;
using Octokit.Webhooks.Events.Issues;
using Octokit.Webhooks.Models;

namespace DevTeam.Backend;

public sealed class GithubWebHookProcessor(ILogger<GithubWebHookProcessor> logger, AgentWorker client) : WebhookEventProcessor
{
    private readonly ILogger<GithubWebHookProcessor> _logger = logger;
    private readonly AgentWorker _client = client;

    protected override async Task ProcessIssuesWebhookAsync(WebhookHeaders headers, IssuesEvent issuesEvent, IssuesAction action)
    {
        try
        {
            ArgumentNullException.ThrowIfNull(headers, nameof(headers));
            ArgumentNullException.ThrowIfNull(issuesEvent, nameof(issuesEvent));
            ArgumentNullException.ThrowIfNull(action, nameof(action));

            _logger.LogInformation("Processing issue event");
            var org = issuesEvent.Repository?.Owner.Login ?? throw new InvalidOperationException("Repository owner login is null");
            var repo = issuesEvent.Repository?.Name ?? throw new InvalidOperationException("Repository name is null");
            var issueNumber = issuesEvent.Issue?.Number ?? throw new InvalidOperationException("Issue number is null");
            var input = issuesEvent.Issue?.Body ?? string.Empty;
            // Assumes the label follows the following convention: Skill.Function example: PM.Readme
            // Also, we've introduced the Parent label, that ties the sub-issue with the parent issue
            var labels = issuesEvent.Issue?.Labels
                                    .Select(l => l.Name.Split('.'))
                                    .Where(parts => parts.Length == 2)
                                    .ToDictionary(parts => parts[0], parts => parts[1]);
            if (labels == null || labels.Count == 0)
            {
                _logger.LogWarning("No labels found in issue. Skipping processing.");
                return;
            }

            long? parentNumber = labels.TryGetValue("Parent", out string? value) ? long.Parse(value) : null;
            var skillName = labels.Keys.Where(k => k != "Parent").FirstOrDefault();

            if (skillName == null)
            {
                _logger.LogWarning("No skill name found in issue. Skipping processing.");
                return;
            }

            var suffix = $"{org}-{repo}";
            if (issuesEvent.Action == IssuesAction.Opened)
            {
                _logger.LogInformation("Processing HandleNewAsk");
                await HandleNewAsk(issueNumber, skillName, labels[skillName], suffix, input, org, repo);
            }
            else if (issuesEvent.Action == IssuesAction.Closed && issuesEvent.Issue?.User.Type.Value == UserType.Bot)
            {
                _logger.LogInformation("Processing HandleClosingIssue");
                await HandleClosingIssue(issueNumber, skillName, labels[skillName], suffix);
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
        ArgumentNullException.ThrowIfNull(headers);
        ArgumentNullException.ThrowIfNull(issueCommentEvent);
        ArgumentNullException.ThrowIfNull(action);

        try
        {
            _logger.LogInformation("Processing issue comment event");
            var org = issueCommentEvent.Repository!.Owner.Login;
            var repo = issueCommentEvent.Repository.Name;
            var issueNumber = issueCommentEvent.Issue.Number;
            var input = issueCommentEvent.Comment.Body;
            // Assumes the label follows the following convention: Skill.Function example: PM.Readme
            var labels = issueCommentEvent.Issue.Labels
                                    .Select(l => l.Name.Split('.'))
                                    .Where(parts => parts.Length == 2)
                                    .ToDictionary(parts => parts[0], parts => parts[1]);
            var skillName = labels.Keys.First(k => k != "Parent");
            long? parentNumber = labels.TryGetValue("Parent", out var value) ? long.Parse(value, CultureInfo.InvariantCulture) : null;
            var suffix = $"{org}-{repo}";

            // we only respond to non-bot comments
            if (issueCommentEvent.Sender!.Type.Value != UserType.Bot)
            {
                await HandleNewAsk(issueNumber, skillName, labels[skillName], suffix, input, org, repo);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Processing issue comment event");
            throw;
        }

    }

    private async Task HandleClosingIssue(long issueNumber, string skillName, string functionName, string suffix)
    {
        var subject = suffix + issueNumber.ToString();

        var evt = (skillName, functionName) switch
        {
            ("PM", "Readme") => new ReadmeChainClosed { }.ToCloudEvent(subject),
            ("DevLead", "Plan") => new DevPlanChainClosed { }.ToCloudEvent(subject),
            ("Developer", "Implement") => new CodeChainClosed { }.ToCloudEvent(subject),
            _ => new CloudEvent() // TODO: default event
        };

        await _client.PublishEventAsync(evt);
    }

    private async Task HandleNewAsk(long issueNumber, string skillName, string functionName, string suffix, string input, string org, string repo)
    {
        try
        {
            _logger.LogInformation("Handling new ask");
            var subject = suffix + issueNumber.ToString();

            var evt = (skillName, functionName) switch
            {
                ("Do", "It") => new NewAsk { Ask = input, IssueNumber = issueNumber, Org = org, Repo = repo }.ToCloudEvent(subject),
                ("PM", "Readme") => new ReadmeRequested { Ask = input, IssueNumber = issueNumber, Org = org, Repo = repo }.ToCloudEvent(subject),
                ("DevLead", "Plan") => new DevPlanRequested { Ask = input, IssueNumber = issueNumber, Org = org, Repo = repo }.ToCloudEvent(subject),
                ("Developer", "Implement") => new CodeGenerationRequested { Ask = input, IssueNumber = issueNumber, Org = org, Repo = repo }.ToCloudEvent(subject),
                _ => new CloudEvent()
            };
            await _client.PublishEventAsync(evt);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Handling new ask");
            throw;
        }
    }
}
