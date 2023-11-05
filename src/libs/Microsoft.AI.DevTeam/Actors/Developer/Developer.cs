using Microsoft.AI.DevTeam.Skills;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public class Dev : SemanticPersona, IDevelopCode
{
    private readonly IKernel _kernel;
    protected override string MemorySegment => "dev-memory"; 

    public Dev(IKernel kernel, [PersistentState("state", "messages")]IPersistentState<SemanticPersonaState> state) : base(state)
    {
        _kernel = kernel;
    }

    public async Task<string> GenerateCode(string ask)
    {
        var function = _kernel.LoadFunction(nameof(Developer), nameof(Developer.Implement));
        var context = new ContextVariables();
        if (_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
        _state.State.History.Add(new ChatHistoryItem
        {
            Message = ask,
            Order = _state.State.History.Count + 1,
            UserType = ChatUserType.User
        });
        await AddWafContext(_kernel, ask, context);
        context.Set("input", ask);

        var result = await _kernel.RunAsync(context, function);
        var resultMessage = result.ToString();
        _state.State.History.Add(new ChatHistoryItem
        {
            Message = resultMessage,
            Order = _state.State.History.Count + 1,
            UserType = ChatUserType.Agent
        });
        await _state.WriteStateAsync();

        return resultMessage;
    }

   

    public Task<string> ReviewPlan(string plan)
    {
        throw new NotImplementedException();
    }

    public Task<string> BuildUnderstanding(string content)
    {
        throw new NotImplementedException();
    }
}
