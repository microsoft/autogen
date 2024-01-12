using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

public class Architect : SemanticPersona, IArchitectSolutions
{
    public Architect( [PersistentState("state", "messages")]IPersistentState<SemanticPersonaState> state) : base(state)
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
    public async override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.NewAsk:
                break;
            default:
                break;
        }
    }
}

public interface IArchitectSolutions : IGrainWithIntegerCompoundKey
{
    Task<string> ReviewPlan(string plan);
    Task<string> GenerateProjectStructure(string ask);
}