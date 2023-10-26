namespace Microsoft.AI.DevTeam;

public interface ILookupMetadata : IGrainWithStringKey
{
    Task<NewIssueResponse> GetMetadata(int key);
    Task StoreMetadata(List<StoreMetadataPairs> pairs);
}
