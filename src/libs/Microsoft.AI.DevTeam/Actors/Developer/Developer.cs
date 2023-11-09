using Microsoft.AI.DevTeam.Skills;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public class Dev : SemanticPersona, IDevelopCode
{
    private readonly IKernel _kernel;
    private readonly ILogger<Dev> _logger;

    protected override string MemorySegment => "dev-memory";

    public Dev(IKernel kernel, [PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state, ILogger<Dev> logger) : base(state)
    {
        _kernel = kernel;
        _logger = logger;
    }

    public async Task<string> GenerateCode(string ask)
    {
        try
        {
            var function = _kernel.CreateSemanticFunction(Developer.Implement, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.8, TopP = 1 });
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
        catch(Exception ex)
        {
            _logger.LogError(ex, "Error generating code");
            return default;
        }
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
