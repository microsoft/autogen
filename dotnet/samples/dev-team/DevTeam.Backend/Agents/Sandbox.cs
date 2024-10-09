// TODO: Reimplement using ACA Sessions
// using DevTeam.Events;
// using Microsoft.AutoGen.Agents.Abstractions;
// using Microsoft.AutoGen.Agents.Client;

// namespace DevTeam.Backend;

// public sealed class Sandbox : AgentBase
// {
//     private const string ReminderName = "SandboxRunReminder";
//     private readonly IManageAzure _azService;
//     // private readonly IPersistentState<SandboxMetadata> _state;

//     public Sandbox(IManageAzure azService)
//     {
//         _azService = azService;
//         _state = state;
//     }
//     public override async Task HandleEvent(Event item)
//     {
//         ArgumentNullException.ThrowIfNull(item);

//         switch (item.Type)
//         {
//             case nameof(EventTypes.SandboxRunCreated):
//                 {
//                     var context = item.ToGithubContext();
//                     await ScheduleCommitSandboxRun(context.Org, context.Repo, context.ParentNumber!.Value, context.IssueNumber);
//                     break;
//                 }

//             default:
//                 break;
//         }
//     }
//     public async Task ScheduleCommitSandboxRun(string org, string repo, long parentIssueNumber, long issueNumber)
//     {
//         await StoreState(org, repo, parentIssueNumber, issueNumber);
//         _reminder = await _reminderRegistry.RegisterOrUpdateReminder(
//             callingGrainId: this.GetGrainId(),
//             reminderName: ReminderName,
//             dueTime: TimeSpan.Zero,
//             period: TimeSpan.FromMinutes(1));
//     }

//     async Task IRemindable.ReceiveReminder(string reminderName, TickStatus status)
//     {
//         if (!_state.State.IsCompleted)
//         {
//             var sandboxId = $"sk-sandbox-{_state.State.Org}-{_state.State.Repo}-{_state.State.ParentIssueNumber}-{_state.State.IssueNumber}".ToUpperInvariant();

//             if (await _azService.IsSandboxCompleted(sandboxId))
//             {
//                 await _azService.DeleteSandbox(sandboxId);
//                 await PublishEvent(new Event
//                 {
//                     Namespace = this.GetPrimaryKeyString(),
//                     Type = nameof(GithubFlowEventType.SandboxRunFinished),
//                     Data = new Dictionary<string, string>
//                     {
//                         ["org"] = _state.State.Org,
//                         ["repo"] = _state.State.Repo,
//                         ["issueNumber"] = _state.State.IssueNumber.ToString(),
//                         ["parentNumber"] = _state.State.ParentIssueNumber.ToString()
//                     }
//                 });
//                 await Cleanup();
//             }
//         }
//         else
//         {
//             await Cleanup();
//         }
//     }

//     private async Task StoreState(string org, string repo, long parentIssueNumber, long issueNumber)
//     {
//         _state.State.Org = org;
//         _state.State.Repo = repo;
//         _state.State.ParentIssueNumber = parentIssueNumber;
//         _state.State.IssueNumber = issueNumber;
//         _state.State.IsCompleted = false;
//         await _state.WriteStateAsync();
//     }

//     private async Task Cleanup()
//     {
//         _state.State.IsCompleted = true;
//         await _reminderRegistry.UnregisterReminder(
//             this.GetGrainId(), _reminder);
//         await _state.WriteStateAsync();
//     }

// }

// public class SandboxMetadata
// {
//     public string Org { get; set; } = default!;
//     public string Repo { get; set; } = default!;
//     public long ParentIssueNumber { get; set; }
//     public long IssueNumber { get; set; }
//     public bool IsCompleted { get; set; }
// }
