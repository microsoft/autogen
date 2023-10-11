namespace MS.AI.DevTeam;
using Orleans.Runtime;
using Orleans.Timers;

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
    public async Task ScheduleCommitSandboxRun(CommitRequest commitRequest, MarkTaskCompleteRequest markTaskCompleteRequest, SandboxRequest sandboxRequest)
    {
        await StoreState(commitRequest, markTaskCompleteRequest, sandboxRequest);
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
            var sandboxId =  $"sk-sandbox-{_state.State.SandboxRequest.Org}-{_state.State.SandboxRequest.Repo}-{_state.State.SandboxRequest.ParentIssueNumber}-{_state.State.SandboxRequest.IssueNumber}";
            if (await _azService.IsSandboxCompleted(sandboxId))
            {
                await _azService.DeleteSandbox(sandboxId);
                await _ghService.CommitToBranch(_state.State.CommitRequest);
                await _ghService.MarkTaskComplete(_state.State.MarkTaskCompleteRequest);
                await Cleanup();
            }
        }
        else
        {
            await Cleanup();
        }
    }

    private async Task StoreState(CommitRequest commitRequest, MarkTaskCompleteRequest markTaskCompleteRequest, SandboxRequest sandboxRequest)
    {
        _state.State.CommitRequest = commitRequest;
        _state.State.MarkTaskCompleteRequest = markTaskCompleteRequest;
        _state.State.SandboxRequest = sandboxRequest;
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
    public CommitRequest CommitRequest { get; set; }
    public MarkTaskCompleteRequest MarkTaskCompleteRequest { get; set; }
    public SandboxRequest SandboxRequest { get; set; }
    public bool IsCompleted { get; set; }
}
