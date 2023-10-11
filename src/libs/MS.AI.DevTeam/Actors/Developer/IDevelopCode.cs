namespace MS.AI.DevTeam;

public interface IDevelopCode : IGrainWithIntegerCompoundKey, IChatHistory
{
    Task<string> GenerateCode(string ask);
    Task<string> ReviewPlan(string plan);
}