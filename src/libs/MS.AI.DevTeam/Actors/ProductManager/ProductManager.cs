using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace MS.AI.DevTeam;
public class ProductManager : SemanticPersona, IManageProduct
{
    private readonly IKernel _kernel;
    protected override string MemorySegment => "pm-memory";

    public ProductManager(IKernel kernel,[PersistentState("state", "messages")] IPersistentState<ChatHistory> state) : base(state)
    {
        _kernel = kernel;
    }
    public async Task<string> CreateReadme(string ask)
    {
        var function = _kernel.LoadFunction(nameof(PM), nameof(PM.Readme));
        var context = new ContextVariables();
        context.Set("input", ask);
        if(_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
        _state.State.History.Add(new ChatHistoryItem
        {
            Message = ask,
            Order = _state.State.History.Count + 1,
            UserType = ChatUserType.User
        });
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
}
