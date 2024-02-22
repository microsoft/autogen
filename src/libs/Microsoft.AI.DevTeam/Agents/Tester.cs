using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

public class Tester : Agent
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