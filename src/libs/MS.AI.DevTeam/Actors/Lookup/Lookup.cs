using Orleans.Runtime;

namespace MS.AI.DevTeam;

public class Lookup : Grain, ILookupMetadata
{
    protected readonly IPersistentState<ConductorLookup> _state;
    public Lookup([PersistentState("state", "messages")] IPersistentState<ConductorLookup> state)
    {
        _state = state;
    }

    public Task<NewIssueResponse> GetMetadata(int key)
    {
        return Task.FromResult(_state.State.Metadata[key]);
    }

    public Task StoreMetadata(List<StoreMetadataPairs> pairs)
    {
        if(_state.State.Metadata == null) _state.State.Metadata = new Dictionary<int, NewIssueResponse>();
        foreach(var pair in pairs)
        {
            _state.State.Metadata[pair.Key] = pair.Value;
        }
        return _state.WriteStateAsync();
    }
}

[Serializable]
public class ConductorLookup
{
    public Dictionary<int, NewIssueResponse> Metadata { get; set; }
}

[GenerateSerializer]
public class StoreMetadataPairs
{
    [Id(0)]
    public int Key { get; set; }
    [Id(1)]
    public NewIssueResponse Value { get; set; }
}