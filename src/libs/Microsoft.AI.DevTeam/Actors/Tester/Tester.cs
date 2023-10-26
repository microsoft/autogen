using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public class Tester : SemanticPersona, ITestCode
{
    public Tester(
        [PersistentState("state", "messages")]IPersistentState<ChatHistory> state) : base(state)
    {
        
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