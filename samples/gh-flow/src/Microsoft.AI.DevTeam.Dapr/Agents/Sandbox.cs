using Dapr.Actors.Runtime;
using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Dapr;
using Microsoft.AI.DevTeam.Dapr.Events;

namespace Microsoft.AI.DevTeam.Dapr;
public class Sandbox : Agent, IDaprAgent, IRemindable
{
    private const string ReminderName = "SandboxRunReminder";
    public string StateStore = "agents-statestore";
    private readonly IManageAzure _azService;

    public Sandbox(ActorHost host, DaprClient client, IManageAzure azService) : base(host, client)
    {
        _azService = azService;
    }

    public override async Task HandleEvent(Event item)
    {
        switch(item.Type)
       {
           case nameof(GithubFlowEventType.SandboxRunCreated):
            {
                var context = item.ToGithubContext();
                await ScheduleCommitSandboxRun(context.Org, context.Repo, context.ParentNumber.Value, context.IssueNumber);
            }
             break;
           
           default:
               break;
       }
    }

    public async Task ScheduleCommitSandboxRun(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        await StoreState(org, repo, parentIssueNumber, issueNumber);
        await this.RegisterReminderAsync(
            ReminderName, 
            null,
            TimeSpan.Zero, 
            TimeSpan.FromMinutes(1));
    }

    private async Task StoreState(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        var state  = new SandboxMetadata {
            Org = org,
            Repo = repo,
            IssueNumber = issueNumber,
            ParentIssueNumber = parentIssueNumber,
            IsCompleted = false
        };
        await StateManager.SetStateAsync(
                StateStore,
                state);
    }
    private async Task Cleanup()
    {
        var agentState = await StateManager.GetStateAsync<SandboxMetadata>(StateStore);
        agentState.IsCompleted = true;
        await UnregisterReminderAsync(ReminderName);
        await StateManager.SetStateAsync(
                StateStore,
                agentState);
    }

    public async Task ReceiveReminderAsync(string reminderName, byte[] state, TimeSpan dueTime, TimeSpan period)
    {
        var agentState = await StateManager.GetStateAsync<SandboxMetadata>(StateStore);
        if (!agentState.IsCompleted)
        {
            var sandboxId =  $"sk-sandbox-{agentState.Org}-{agentState.Repo}-{agentState.ParentIssueNumber}-{agentState.IssueNumber}";
            if (await _azService.IsSandboxCompleted(sandboxId))
            {
                await _azService.DeleteSandbox(sandboxId);
                var data = new Dictionary<string, string> {
                        { "org", agentState.Org },
                        { "repo", agentState.Repo },
                        { "issueNumber", agentState.IssueNumber.ToString() },
                        { "parentNumber", agentState.ParentIssueNumber.ToString() }
                    };
                var subject = $"{agentState.Org}-{agentState.Repo}-{agentState.IssueNumber}";
                await PublishEvent(Consts.PubSub,Consts.MainTopic, new Event {
                     Type = nameof(GithubFlowEventType.SandboxRunFinished),
                     Subject = subject,
                    Data = data
                });
                await Cleanup();
            }
        }
        else
        {
            await Cleanup();
        }
    }
}

public class SandboxMetadata
{
    public string Org { get; set; }
    public string Repo { get; set; }
    public long ParentIssueNumber { get; set; }
    public long IssueNumber { get; set; }
    public bool IsCompleted { get; set; }
}