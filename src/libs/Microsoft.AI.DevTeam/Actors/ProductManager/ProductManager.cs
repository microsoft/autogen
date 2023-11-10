using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;
public class ProductManager : SemanticPersona, IManageProduct
{
    private readonly IKernel _kernel;
    private readonly ISemanticTextMemory _memory;
    private readonly ILogger<ProductManager> _logger;

    protected override string MemorySegment => "pm-memory";

    public ProductManager([PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state, IKernel kernel, ISemanticTextMemory memory, ILogger<ProductManager> logger) : base(state)
    {
        _kernel = kernel;
        _memory = memory;
        _logger = logger;
    }
    public async Task<string> CreateReadme(string ask)
    {
        try
        {
            var function = _kernel.CreateSemanticFunction(PM.Readme, new OpenAIRequestSettings { MaxTokens = 10000, Temperature = 0.6, TopP = 1 });
            var context = new ContextVariables();
            context.Set("input", ask);
            if (_state.State.History == null) _state.State.History = new List<ChatHistoryItem>();
            _state.State.History.Add(new ChatHistoryItem
            {
                Message = ask,
                Order = _state.State.History.Count + 1,
                UserType = ChatUserType.User
            });
            await AddWafContext(_memory, ask, context);
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
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating readme");
            return default;
        }
    }
}
