using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace MS.AI.DevTeam;

public class Developer : SemanticPersona, IDevelopCode
{
    private readonly IKernel _kernel;
    protected override string MemorySegment => "dev-memory"; 

    public Developer(IKernel kernel, [PersistentState("state", "messages")]IPersistentState<ChatHistory> state) : base(state)
    {
        _kernel = kernel;
    }

    public async Task<string> GenerateCode(string ask)
    {
        var function = _kernel.LoadFunction(nameof(Dev), nameof(Dev.Implement));
        var context = new ContextVariables();
        if (_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
        _state.State.History.Add(new ChatHistoryItem{
            Message = ask,
            Order = _state.State.History.Count+1,
            UserType = ChatUserType.User
        });
        context.Set("input", ask);

        var result = await _kernel.RunAsync(context, function);
        var resultMessage = result.ToString();
        _state.State.History.Add(new ChatHistoryItem{
            Message = resultMessage,
            Order = _state.State.History.Count+1,
            UserType = ChatUserType.Agent
        });
        await _state.WriteStateAsync();
        
        return resultMessage;
    }

    public Task<string> ReviewPlan(string plan)
    {
        throw new NotImplementedException();
    }
}
