namespace MS.AI.DevTeam;

public interface ILeadDevelopment: IGrainWithIntegerCompoundKey, IChatHistory
{
    Task<string> CreatePlan(string ask);
    Task<DevLeadPlanResponse> GetLatestPlan();
}