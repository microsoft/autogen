namespace MS.AI.DevTeam;

public interface IManageSandbox : IGrainWithIntegerCompoundKey
{
    Task ScheduleCommitSandboxRun(CommitRequest commitRequest, MarkTaskCompleteRequest markTaskCompleteRequest, SandboxRequest sandboxRequest);
}