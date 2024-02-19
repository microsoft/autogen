namespace Microsoft.AI.DevTeam;

public interface IDevelopCode : IGrainWithIntegerCompoundKey, IChatHistory, IUnderstand
{
    Task<string> GenerateCode(string ask);
    Task<string> ReviewPlan(string plan);
}