using Orleans.Runtime;

namespace MS.AI.DevTeam;

public class Architect : SemanticPersona, IArchitectSolutions
{
    public Architect( [PersistentState("state", "messages")]IPersistentState<ChatHistory> state) : base(state)
    {
        
    }
    public Task<string> GenerateProjectStructure(string ask)
    {
        throw new NotImplementedException();
    }

    public Task<string> ReviewPlan(string plan)
    {
        throw new NotImplementedException();
    }
}

public interface IArchitectSolutions : IGrainWithIntegerCompoundKey
{
    Task<string> ReviewPlan(string plan);
    Task<string> GenerateProjectStructure(string ask);
}