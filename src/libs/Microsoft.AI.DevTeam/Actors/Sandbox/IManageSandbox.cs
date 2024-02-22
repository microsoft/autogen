namespace Microsoft.AI.DevTeam;

public interface IManageSandbox : IGrainWithIntegerCompoundKey
{
    Task ScheduleCommitSandboxRun(string org, string repo, long parentIssueNumber, long issueNumber);
}