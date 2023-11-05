namespace Microsoft.AI.DevTeam;

public interface IManageProduct : IGrainWithIntegerCompoundKey, IChatHistory, IUnderstand
{
    Task<string> CreateReadme(string ask);
}