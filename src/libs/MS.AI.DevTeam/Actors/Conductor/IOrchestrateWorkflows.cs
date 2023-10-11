using Orleans.Concurrency;

namespace MS.AI.DevTeam;

public interface IOrchestrateWorkflows : IGrainWithIntegerCompoundKey
{
    [OneWay]
    Task InitialFlow(string input, string org, string repo, long parentNumber);
    [OneWay]
    Task ImplementationFlow(DevLeadPlanResponse plan, string org, string repo, int parentNumber);
}