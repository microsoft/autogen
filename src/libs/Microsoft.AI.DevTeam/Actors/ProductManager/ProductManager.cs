using Microsoft.AI.DevTeam.Skills;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;
public class ProductManager : SemanticPersona, IManageProduct
{
    private readonly IKernel _kernel;
    protected override string MemorySegment => "pm-memory";

    public ProductManager(IKernel kernel,[PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state) : base(state)
    {
        _kernel = kernel;
    }
    public async Task<string> CreateReadme(string ask)
    {
        var function = _kernel.CreateSemanticFunction(PM.Readme, new OpenAIRequestSettings { MaxTokens = 10000, Temperature = 0.6, TopP = 1 });
        var context = new ContextVariables();
        context.Set("input", ask);
        if(_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
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
}
