using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

public class Tester : SemanticPersona, ITestCode
{
    public Tester(
        [PersistentState("state", "messages")]IPersistentState<SemanticPersonaState> state) : base(state)
    {
        
    }

    public override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        throw new NotImplementedException();
    }

    public Task<string> ReviewPlan(string plan)
    {
        throw new NotImplementedException();
    }

    public Task<string> TestCode(string ask)
    {
        throw new NotImplementedException();
    }
}

public interface ITestCode  : IGrainWithIntegerCompoundKey
{
    Task<string> TestCode(string ask);
    Task<string> ReviewPlan(string plan);
}