namespace Microsoft.AI.DevTeam;

public interface ILeadDevelopment: IGrainWithIntegerCompoundKey, IChatHistory, IUnderstand
{
    Task<string> CreatePlan(string ask);
    Task<DevLeadPlanResponse> GetLatestPlan();
}