using Orleans.Concurrency;

namespace Microsoft.AI.DevTeam;

public interface IIngestRepo : IGrainWithStringKey
{
    [OneWay]
    Task IngestionFlow(string org, string repo, string branch);
}