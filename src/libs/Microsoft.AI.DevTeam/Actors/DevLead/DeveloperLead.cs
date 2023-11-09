using Microsoft.AI.DevTeam.Skills;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI;
using Microsoft.SemanticKernel.Orchestration;
using Orleans.Runtime;
using System.Text.Json;

namespace Microsoft.AI.DevTeam;
public class DeveloperLead : SemanticPersona, ILeadDevelopment
{
    private readonly IKernel _kernel;
    protected override string MemorySegment => "dev-lead-memory";

    public DeveloperLead(IKernel kernel, [PersistentState("state", "messages")] IPersistentState<SemanticPersonaState> state) : base(state)
    {
        _kernel = kernel;
    }
    public async Task<string> CreatePlan(string ask)
    {
        // var architectId = Guid.NewGuid();
        // var plan = "this is my plan";
        // var architect = GrainFactory.GetGrain<IArchitectSolutions>(architectId);
        // var review = architect.ReviewPlan(plan);
        // return Task.FromResult(plan);

        var function = _kernel.CreateSemanticFunction(DevLead.Plan, new OpenAIRequestSettings { MaxTokens = 15000, Temperature = 0.4, TopP = 1 });
        var context = new ContextVariables();
        context.Set("input", ask);
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

    public Task<DevLeadPlanResponse> GetLatestPlan()
    {
        var plan = _state.State.History.Last().Message;
        var response = JsonSerializer.Deserialize<DevLeadPlanResponse>(plan);
        return Task.FromResult(response);
    }

    public Task<string> BuildUnderstanding(string content)
    {
        throw new NotImplementedException();
    }
}

[GenerateSerializer]
public class DevLeadPlanResponse
{
    [Id(0)]
    public List<Step> steps { get; set; }
}

[GenerateSerializer]
public class Step
{
    [Id(0)]
    public string description { get; set; }
    [Id(1)]
    public string step { get; set; }
    [Id(2)]
    public List<Subtask> subtasks { get; set; }
}

[GenerateSerializer]
public class Subtask
{
    [Id(0)]
    public string subtask { get; set; }
    [Id(1)]
    public string prompt { get; set; }
}




