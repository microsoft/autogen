using System.Globalization;
using System.Text.Json;
using Agents;
using Octokit.Webhooks;
using Octokit.Webhooks.Events;
using Octokit.Webhooks.Events.IssueComment;
using Octokit.Webhooks.Events.Issues;
using Octokit.Webhooks.Models;

namespace DevTeam.Backend;

public sealed class GithubWebHookProcessor(ILogger<GithubWebHookProcessor> logger, AgentClient client) : WebhookEventProcessor
{
    private readonly ILogger<GithubWebHookProcessor> _logger = logger;
    private readonly AgentClient _client = client;

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
                await HandleNewAsk(issueNumber, parentNumber, skillName, labels[skillName], suffix, input, org, repo);
            }
            else if (issuesEvent.Action == IssuesAction.Closed && issuesEvent.Issue?.User.Type.Value == UserType.Bot)
            {
                _logger.LogInformation("Processing HandleClosingIssue");
                await HandleClosingIssue(issueNumber, parentNumber, skillName, labels[skillName], suffix, org, repo);
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
                await HandleNewAsk(issueNumber, parentNumber, skillName, labels[skillName], suffix, input, org, repo);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Processing issue comment event");
            throw;
        }

    }

    private async Task HandleClosingIssue(long issueNumber, long? parentNumber, string skillName, string functionName, string suffix, string org, string repo)
    {
        var subject = suffix + issueNumber.ToString();

        var eventType = (skillName, functionName) switch
        {
            //("PM", "Readme") => nameof(EventTypes.ReadmeChainClosed),
            //("DevLead", "Plan") => nameof(EventTypes.DevPlanChainClosed),
            //("Developer", "Implement") => nameof(EventTypes.CodeChainClosed),
            _ => "asd"
        };
        var data = new Dictionary<string, string>
        {
            ["org"] = org,
            ["repo"] = repo,
            ["issueNumber"] = issueNumber.ToString(),
            ["parentNumber"] = (parentNumber ?? 0).ToString()
        };
        await _client.PublishEventAsync(new CloudEvent
        {
            Source = subject,
            Type = eventType,
            TextData = JsonSerializer.Serialize(data),
        });
        await Task.CompletedTask;
    }

    private async Task HandleNewAsk(long issueNumber, long? parentNumber, string skillName, string functionName, string suffix, string input, string org, string repo)
    {
        try
        {
            _logger.LogInformation("Handling new ask");
            var subject = suffix + issueNumber.ToString();

            var eventType = (skillName, functionName) switch
            {
                //("Do", "It") => nameof(EventTypes.NewAsk),
                //("PM", "Readme") => nameof(EventTypes.ReadmeRequested),
                //("DevLead", "Plan") => nameof(EventTypes.DevPlanRequested),
                //("Developer", "Implement") => nameof(EventTypes.CodeGenerationRequested),
                _ => "nameof(EventTypes.NewAsk)"
            };
            var data = new Dictionary<string, string>
            {
                { "org", org },
                { "repo", repo },
                { "issueNumber", issueNumber.ToString() },
                { "parentNumber", (parentNumber ?? 0).ToString()},
                { "input", input}

            };
            await _client.PublishEventAsync(new CloudEvent
            {
                Source = subject,
                Type = eventType,
                TextData = JsonSerializer.Serialize(data),
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Handling new ask");
            throw;
        }
    }
}
