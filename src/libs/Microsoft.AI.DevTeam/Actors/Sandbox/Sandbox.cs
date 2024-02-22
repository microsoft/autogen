using Orleans.Runtime;
using Orleans.Timers;

namespace Microsoft.AI.DevTeam;
public class Sandbox : Grain, IManageSandbox, IRemindable
{
    private const string ReminderName = "SandboxRunReminder";
    private readonly IManageGithub _ghService;
    private readonly IManageAzure _azService;
    private readonly IReminderRegistry _reminderRegistry;
    private IGrainReminder? _reminder;

    protected readonly IPersistentState<SandboxMetadata> _state;

    public Sandbox([PersistentState("state", "messages")] IPersistentState<SandboxMetadata> state, IManageGithub ghService,
                    IReminderRegistry reminderRegistry, IManageAzure azService)
    {
        _ghService = ghService;
        _reminderRegistry = reminderRegistry;
        _azService = azService;
        _state = state;
    }
    public async Task ScheduleCommitSandboxRun(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        await StoreState(org, repo, parentIssueNumber, issueNumber);
        _reminder = await _reminderRegistry.RegisterOrUpdateReminder(
            callingGrainId: this.GetGrainId(),
            reminderName: ReminderName,
            dueTime: TimeSpan.Zero,
            period: TimeSpan.FromMinutes(1));
    }

    async Task IRemindable.ReceiveReminder(string reminderName, TickStatus status)
    {
        if (!_state.State.IsCompleted)
        {
            var sandboxId =  $"sk-sandbox-{_state.State.Org}-{_state.State.Repo}-{_state.State.ParentIssueNumber}-{_state.State.IssueNumber}";
            if (await _azService.IsSandboxCompleted(sandboxId))
            {
                await _azService.DeleteSandbox(sandboxId);
                await _ghService.CommitToBranch(_state.State.Org, _state.State.Repo, _state.State.ParentIssueNumber, _state.State.IssueNumber, _state.State.RootDir, _state.State.Branch);
                await _ghService.MarkTaskComplete(_state.State.Org, _state.State.Repo, _state.State.CommentId);
                await Cleanup();
            }
        }
        else
        {
            await Cleanup();
        }
    }

    private async Task StoreState(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        _state.State.Org = org;
        _state.State.Repo = repo;
        _state.State.ParentIssueNumber = parentIssueNumber;
        // TODO: Add all of the state properties
        _state.State.IsCompleted = false;
        await _state.WriteStateAsync();
    }

    private async Task Cleanup()
    {
        _state.State.IsCompleted = true;
        await _reminderRegistry.UnregisterReminder(
            this.GetGrainId(), _reminder);
        await _state.WriteStateAsync();
    }
}


public class SandboxMetadata
{
    public string Org { get; set; }
    public string Repo { get; set; }
    public long ParentIssueNumber { get; set; }
    public long IssueNumber { get; set; }
    public string RootDir { get; set; }
    public string Branch { get; set; }
    public int CommentId { get; set; }

    public bool IsCompleted { get; set; }
}
