// Copyright (c) Microsoft Corporation. All rights reserved.
// Hubber.cs

using System.Text.Json;
using DevTeam.Backend.Services;
using Microsoft.AutoGen.Core;

namespace DevTeam.Backend.Agents;

[TopicSubscription(Consts.TopicName)]
public class Hubber([FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, IManageGithub ghService)
    : Agent(typeRegistry),
    IHandle<NewAsk>,
    IHandle<ReadmeGenerated>,
    IHandle<DevPlanGenerated>,
    IHandle<DevPlanCreated>,
    IHandle<ReadmeStored>,
    IHandle<CodeGenerated>
{
    public async Task Handle(NewAsk item, CancellationToken cancellationToken = default)
    {
        var pmIssue = await CreateIssue(item.Org, item.Repo, item.Ask, "PM.Readme", item.IssueNumber);
        var devLeadIssue = await CreateIssue(item.Org, item.Repo, item.Ask, "DevLead.Plan", item.IssueNumber);
        await PostComment(item.Org, item.Repo, item.IssueNumber, $" - #{pmIssue} - tracks PM.Readme");
        await PostComment(item.Org, item.Repo, item.IssueNumber, $" - #{devLeadIssue} - tracks DevLead.Plan");
        await CreateBranch(item.Org, item.Repo, $"sk-{item.IssueNumber}");
    }

    public async Task Handle(ReadmeGenerated item, CancellationToken cancellationToken = default)
    {
        var contents = string.IsNullOrEmpty(item.Readme) ? "Sorry, I got tired, can you try again please? " : item.Readme;
        await PostComment(item.Org, item.Repo, item.IssueNumber, contents);
    }

    public async Task Handle(DevPlanGenerated item, CancellationToken cancellationToken = default)
    {
        var contents = string.IsNullOrEmpty(item.Plan) ? "Sorry, I got tired, can you try again please? " : item.Plan;
        await PostComment(item.Org, item.Repo, item.IssueNumber, contents);
    }

    public async Task Handle(CodeGenerated item, CancellationToken cancellationToken = default)
    {
        var contents = string.IsNullOrEmpty(item.Code) ? "Sorry, I got tired, can you try again please? " : item.Code;
        await PostComment(item.Org, item.Repo, item.IssueNumber, contents);
    }

    public async Task Handle(DevPlanCreated item, CancellationToken cancellationToken = default)
    {
        var plan = JsonSerializer.Deserialize<DevLeadPlan>(item.Plan);
        var prompts = plan!.Steps.SelectMany(s => s.Subtasks!.Select(st => st.Prompt));

        foreach (var prompt in prompts)
        {
            var functionName = "Developer.Implement";
            var issue = await CreateIssue(item.Org, item.Repo, prompt!, functionName, item.IssueNumber);
            var commentBody = $" - #{issue} - tracks {functionName}";
            await PostComment(item.Org, item.Repo, item.IssueNumber, commentBody);
        }
    }

    public async Task Handle(ReadmeStored item, CancellationToken cancellationToken = default)
    {
        var branch = $"sk-{item.ParentNumber}";
        await CommitToBranch(item.Org, item.Repo, item.ParentNumber, item.IssueNumber, "output", branch);
        await CreatePullRequest(item.Org, item.Repo, item.ParentNumber, branch);
    }

    public async Task<int> CreateIssue(string org, string repo, string input, string function, long parentNumber)
    {
        return await ghService.CreateIssue(org, repo, input, function, parentNumber);
    }
    public async Task PostComment(string org, string repo, long issueNumber, string comment)
    {
        await ghService.PostComment(org, repo, issueNumber, comment);
    }
    public async Task CreateBranch(string org, string repo, string branch)
    {
        await ghService.CreateBranch(org, repo, branch);
    }
    public async Task CreatePullRequest(string org, string repo, long issueNumber, string branch)
    {
        await ghService.CreatePR(org, repo, issueNumber, branch);
    }
    public async Task CommitToBranch(string org, string repo, long parentNumber, long issueNumber, string rootDir, string branch)
    {
        await ghService.CommitToBranch(org, repo, parentNumber, issueNumber, rootDir, branch);
    }
}
